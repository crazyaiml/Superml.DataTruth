"""
AI Field Describer

Uses AI to generate business-friendly names and descriptions for database fields.
Similar to ThoughtSpot's AI-powered field understanding.
"""

import logging
import re
from typing import Dict, List, Optional

from src.config.settings import get_settings
from src.llm.client import get_llm_client
from src.connection.models import ColumnMetadata, TableMetadata
from src.fieldmap.models import FieldMapping

logger = logging.getLogger(__name__)

# Singleton instance
_ai_describer = None


class AIFieldDescriber:
    """
    Generates business-friendly field names and descriptions using AI.
    
    ThoughtSpot Step 2: AI-powered field description and classification.
    """
    
    def __init__(self):
        """Initialize AI describer."""
        self.settings = get_settings()
        self.llm_client = get_llm_client()
    
    def describe_table(
        self, table: TableMetadata, sample_data: Optional[List[Dict]] = None
    ) -> List[FieldMapping]:
        """
        Generate field mappings for all columns in a table.
        
        Args:
            table: Table metadata
            sample_data: Optional sample rows for context
            
        Returns:
            List of field mappings
        """
        logger.info(f"Generating AI descriptions for table {table.name}")
        
        mappings = []
        
        # Process columns in batches for efficiency
        batch_size = 10
        for i in range(0, len(table.columns), batch_size):
            batch = table.columns[i:i + batch_size]
            batch_mappings = self._describe_batch(table.name, batch, sample_data)
            mappings.extend(batch_mappings)
        
        return mappings
    
    def _describe_batch(
        self, table_name: str, columns: List[ColumnMetadata], sample_data: Optional[List[Dict]] = None
    ) -> List[FieldMapping]:
        """Describe a batch of columns using AI."""
        
        # Build prompt
        prompt = self._build_description_prompt(table_name, columns, sample_data)
        
        try:
            # Call LLM
            response = self.llm_client.complete(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data analyst expert. Generate business-friendly names and descriptions for database fields."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse response
            mappings = self._parse_ai_response(table_name, columns, response)
            return mappings
            
        except Exception as e:
            logger.error(f"AI description failed: {e}")
            # Fallback to rule-based descriptions
            return self._generate_fallback_mappings(table_name, columns)
    
    def _build_description_prompt(
        self, table_name: str, columns: List[ColumnMetadata], sample_data: Optional[List[Dict]]
    ) -> str:
        """Build prompt for AI field description."""
        
        prompt = f"""Analyze the following database table and columns. Generate business-friendly names, descriptions, and classifications.

Table: {table_name}

Columns:
"""
        
        for col in columns:
            prompt += f"- {col.name} ({col.data_type})\n"
        
        if sample_data:
            prompt += "\nSample Data:\n"
            for i, row in enumerate(sample_data[:3], 1):
                prompt += f"Row {i}: {row}\n"
        
        prompt += """
For each column, provide:
1. display_name: A clear, business-friendly name (Title Case)
2. description: A concise description of what this field represents
3. synonyms: Alternative names users might search for (comma-separated)
4. category: Business category (sales, finance, operations, customer, product, etc.)
5. is_measure: true if numeric and should be aggregated, false otherwise
6. default_aggregation: If measure, suggest: sum, avg, count, min, max, count_distinct

Format your response as JSON array:
[
  {
    "column_name": "transaction_amount",
    "display_name": "Transaction Amount",
    "description": "The monetary value of the transaction in USD",
    "synonyms": ["amount", "value", "total", "revenue"],
    "category": "finance",
    "is_measure": true,
    "default_aggregation": "sum"
  },
  ...
]
"""
        
        return prompt
    
    def _parse_ai_response(
        self, table_name: str, columns: List[ColumnMetadata], response: str
    ) -> List[FieldMapping]:
        """Parse AI response and create field mappings."""
        
        import json
        
        mappings = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON array found in response")
            
            ai_mappings = json.loads(json_match.group(0))
            
            # Create FieldMapping objects
            for ai_mapping in ai_mappings:
                col_name = ai_mapping.get('column_name')
                
                # Find matching column
                col = next((c for c in columns if c.name == col_name), None)
                if not col:
                    continue
                
                mapping = FieldMapping(
                    table_name=table_name,
                    column_name=col_name,
                    data_type=col.data_type,
                    display_name=ai_mapping.get('display_name', self._to_display_name(col_name)),
                    description=ai_mapping.get('description', ''),
                    synonyms=ai_mapping.get('synonyms', []),
                    is_measure=ai_mapping.get('is_measure', col.is_measure),
                    is_dimension=not ai_mapping.get('is_measure', col.is_measure),
                    default_aggregation=ai_mapping.get('default_aggregation'),
                    category=ai_mapping.get('category'),
                    ai_generated=True,
                    confidence_score=0.85,  # High confidence for AI-generated
                    tags=[ai_mapping.get('category', 'general')]
                )
                
                mappings.append(mapping)
            
            return mappings
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._generate_fallback_mappings(table_name, columns)
    
    def _generate_fallback_mappings(
        self, table_name: str, columns: List[ColumnMetadata]
    ) -> List[FieldMapping]:
        """Generate rule-based mappings as fallback."""
        
        mappings = []
        
        for col in columns:
            mapping = FieldMapping(
                table_name=table_name,
                column_name=col.name,
                data_type=col.data_type,
                display_name=self._to_display_name(col.name),
                description=self._generate_description(col.name, col.data_type),
                synonyms=self._generate_synonyms(col.name),
                is_measure=col.is_measure,
                is_dimension=col.is_dimension,
                default_aggregation=col.default_aggregation,
                ai_generated=False,
                confidence_score=0.6  # Lower confidence for rule-based
            )
            
            mappings.append(mapping)
        
        return mappings
    
    def _to_display_name(self, field_name: str) -> str:
        """Convert technical field name to display name."""
        # Split on underscores and capitalize
        words = field_name.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)
    
    def _generate_description(self, field_name: str, data_type: str) -> str:
        """Generate basic description based on field name patterns."""
        
        name_lower = field_name.lower()
        
        if 'amount' in name_lower or 'revenue' in name_lower:
            return f"The {self._to_display_name(field_name).lower()} in monetary units"
        elif 'count' in name_lower or 'quantity' in name_lower:
            return f"The number of {field_name.replace('_count', '').replace('_quantity', '')}"
        elif 'date' in name_lower:
            return f"The date of {field_name.replace('_date', '')}"
        elif 'id' in name_lower:
            return f"Unique identifier for {field_name.replace('_id', '')}"
        elif 'name' in name_lower:
            return f"The name of the {field_name.replace('_name', '')}"
        elif 'status' in name_lower:
            return f"The current status of the {field_name.replace('_status', '')}"
        else:
            return f"{self._to_display_name(field_name)} field"
    
    def _generate_synonyms(self, field_name: str) -> List[str]:
        """Generate synonyms based on field name."""
        
        synonyms = []
        name_lower = field_name.lower()
        
        # Common synonym mappings
        synonym_map = {
            'amount': ['total', 'value', 'sum'],
            'revenue': ['sales', 'income', 'earnings'],
            'count': ['number', 'quantity', 'total'],
            'date': ['time', 'when'],
            'name': ['title', 'label'],
            'id': ['identifier', 'key'],
        }
        
        for keyword, syns in synonym_map.items():
            if keyword in name_lower:
                synonyms.extend(syns)
        
        return synonyms[:5]  # Limit to 5 synonyms


def get_ai_describer() -> AIFieldDescriber:
    """Get singleton AIFieldDescriber instance."""
    global _ai_describer
    if _ai_describer is None:
        _ai_describer = AIFieldDescriber()
    return _ai_describer
