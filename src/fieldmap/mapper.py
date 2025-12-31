"""
Field Mapper

Maps technical field names to business-friendly names using rules and AI.
"""

import logging
import re
from typing import Dict, List, Optional

from src.fieldmap.models import (
    AggregationRule,
    FieldMapping,
    FieldMappingRule,
)

logger = logging.getLogger(__name__)

# Singleton instance
_field_mapper = None


class FieldMapper:
    """
    Maps technical field names to business-friendly names.
    
    Combines rule-based and AI-generated mappings.
    """
    
    def __init__(self):
        """Initialize field mapper with default rules."""
        self.mapping_rules: List[FieldMappingRule] = []
        self.aggregation_rules: List[AggregationRule] = []
        self.field_mappings: Dict[str, FieldMapping] = {}  # Key: connection_id.table.column
        
        # Load default rules
        self._load_default_rules()
        
        # Load persisted mappings from vector DB
        self._load_from_vector_db()
    
    def _load_default_rules(self):
        """Load default mapping and aggregation rules."""
        
        # Aggregation rules
        self.aggregation_rules = [
            AggregationRule(
                field_pattern=r".*amount.*|.*revenue.*|.*price.*|.*cost.*|.*total.*",
                default_aggregation="sum",
                description="Monetary fields should be summed"
            ),
            AggregationRule(
                field_pattern=r".*count.*|.*quantity.*|.*qty.*|.*num.*",
                default_aggregation="sum",
                description="Count fields should be summed"
            ),
            AggregationRule(
                field_pattern=r".*rate.*|.*percentage.*|.*percent.*|.*ratio.*",
                default_aggregation="avg",
                description="Rates and percentages should be averaged"
            ),
            AggregationRule(
                field_pattern=r".*_id$|.*_key$",
                default_aggregation="count_distinct",
                description="ID fields should count distinct values"
            ),
        ]
        
        # Field mapping rules
        self.mapping_rules = [
            FieldMappingRule(
                technical_pattern=r"(.*)_amount",
                business_name_template=r"\1 Amount",
                description_template=r"Total \1 amount in dollars",
                synonyms=[r"\1 total", r"\1 value", r"\1 sum"],
                format_string="$#,##0.00"
            ),
            FieldMappingRule(
                technical_pattern=r"(.*)_revenue",
                business_name_template=r"\1 Revenue",
                description_template=r"Revenue generated from \1",
                synonyms=[r"\1 sales", r"\1 income"],
                format_string="$#,##0.00"
            ),
            FieldMappingRule(
                technical_pattern=r"(.*)_count",
                business_name_template=r"Number of \1",
                description_template=r"Count of \1 records",
                synonyms=[r"\1 total", r"\1 quantity"]
            ),
            FieldMappingRule(
                technical_pattern=r"(.*)_date",
                business_name_template=r"\1 Date",
                description_template=r"Date when \1 occurred",
                synonyms=[r"\1 time", r"\1 when"]
            ),
            FieldMappingRule(
                technical_pattern=r"(.*)_name",
                business_name_template=r"\1 Name",
                description_template=r"The name of the \1",
                synonyms=[r"\1 title", r"\1 label"]
            ),
        ]
    
    def add_mapping(self, mapping: FieldMapping):
        """Add a field mapping (already persisted to vector DB by caller)."""
        # Use connection_id in key for multi-tenant support
        if mapping.connection_id:
            key = f"{mapping.connection_id}.{mapping.table_name}.{mapping.column_name}"
        else:
            key = f"{mapping.table_name}.{mapping.column_name}"
        self.field_mappings[key] = mapping
    
    def get_mapping(self, table_name: str, column_name: str, connection_id: Optional[str] = None) -> Optional[FieldMapping]:
        """Get field mapping for a specific column."""
        # Try connection-specific key first
        if connection_id:
            key = f"{connection_id}.{table_name}.{column_name}"
            mapping = self.field_mappings.get(key)
            if mapping:
                return mapping
        
        # Fallback to non-connection-specific key for backwards compatibility
        key = f"{table_name}.{column_name}"
        return self.field_mappings.get(key)
    
    def get_display_name(self, table_name: str, column_name: str) -> str:
        """Get business-friendly display name for a field."""
        mapping = self.get_mapping(table_name, column_name)
        if mapping:
            return mapping.display_name
        
        # Fallback: apply rules
        for rule in self.mapping_rules:
            match = re.match(rule.technical_pattern, column_name)
            if match:
                # Replace capture groups in template
                display_name = rule.business_name_template
                for i, group in enumerate(match.groups(), 1):
                    display_name = display_name.replace(f"\\{i}", group)
                return display_name
        
        # Final fallback: title case
        return self._to_title_case(column_name)
    
    def get_aggregation(self, table_name: str, column_name: str) -> Optional[str]:
        """Get default aggregation for a field."""
        mapping = self.get_mapping(table_name, column_name)
        if mapping and mapping.default_aggregation:
            return mapping.default_aggregation
        
        # Apply aggregation rules
        for rule in self.aggregation_rules:
            if re.match(rule.field_pattern, column_name, re.IGNORECASE):
                return rule.default_aggregation
        
        return None
    
    def search_fields(self, query: str) -> List[FieldMapping]:
        """
        Search for fields by business name or synonyms.
        
        Args:
            query: Search query
            
        Returns:
            List of matching field mappings
        """
        query_lower = query.lower()
        matches = []
        
        for mapping in self.field_mappings.values():
            # Check display name
            if query_lower in mapping.display_name.lower():
                matches.append(mapping)
                continue
            
            # Check synonyms
            if any(query_lower in syn.lower() for syn in mapping.synonyms):
                matches.append(mapping)
                continue
            
            # Check description
            if query_lower in mapping.description.lower():
                matches.append(mapping)
        
        return matches
    
    def _to_title_case(self, field_name: str) -> str:
        """Convert snake_case to Title Case."""
        words = field_name.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)
    
    def export_mappings(self) -> List[Dict]:
        """Export all mappings as dictionary list."""
        return [mapping.dict() for mapping in self.field_mappings.values()]
    
    def import_mappings(self, mappings: List[Dict]):
        """Import mappings from dictionary list."""
        for mapping_dict in mappings:
            mapping = FieldMapping(**mapping_dict)
            self.add_mapping(mapping)
    
    def _load_from_vector_db(self):
        """Load all field mappings from vector DB on startup."""
        try:
            from src.vector import get_vector_store
            vector_store = get_vector_store()
            
            print(f"[FieldMapper] Loading field mappings from vector DB...")
            
            # Get all fields from semantic_fields collection
            all_fields = vector_store.fields_collection.get()
            
            print(f"[FieldMapper] Vector DB returned: {len(all_fields.get('metadatas', [])) if all_fields else 0} fields")
            
            if not all_fields or 'metadatas' not in all_fields or not all_fields['metadatas']:
                print("[FieldMapper] No field mappings found in vector DB")
                logger.info("No field mappings found in vector DB")
                return
            
            # Convert vector DB entries to FieldMapping objects
            for i, metadata in enumerate(all_fields['metadatas']):
                try:
                    # Parse synonyms from comma-separated string
                    synonyms_str = metadata.get('synonyms', '')
                    synonyms = [s.strip() for s in synonyms_str.split(',') if s.strip()] if synonyms_str else []
                    
                    # Parse boolean
                    is_measure = metadata.get('is_measure', 'False') == 'True'
                    
                    mapping = FieldMapping(
                        connection_id=metadata.get('connection_id'),
                        table_name=metadata.get('table_name', ''),
                        column_name=metadata.get('column_name', ''),
                        display_name=metadata.get('display_name', ''),
                        description=metadata.get('description', ''),
                        data_type=metadata.get('data_type', ''),
                        is_measure=is_measure,
                        is_dimension=not is_measure,
                        default_aggregation=metadata.get('default_aggregation') or None,
                        format_string=None,
                        ai_generated=False,
                        confidence_score=None,
                        synonyms=synonyms,
                        tags=[],
                        category=None,
                        semantic_type='',
                        business_rule=''
                    )
                    
                    # Add to in-memory cache
                    if mapping.connection_id:
                        key = f"{mapping.connection_id}.{mapping.table_name}.{mapping.column_name}"
                    else:
                        key = f"{mapping.table_name}.{mapping.column_name}"
                    self.field_mappings[key] = mapping
                except Exception as e:
                    logger.warning(f"Failed to load field mapping from vector DB: {e}")
                    continue
            
            print(f"[FieldMapper] ✅ Loaded {len(self.field_mappings)} field mappings from vector DB")
            logger.info(f"Loaded {len(self.field_mappings)} field mappings from vector DB")
        except Exception as e:
            print(f"[FieldMapper] ❌ Failed to load field mappings from vector DB: {e}")
            logger.warning(f"Failed to load field mappings from vector DB: {e}")


def get_field_mapper() -> FieldMapper:
    """Get singleton FieldMapper instance."""
    global _field_mapper
    if _field_mapper is None:
        _field_mapper = FieldMapper()
    return _field_mapper
