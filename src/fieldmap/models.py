"""
Field Mapping Models

Models for field mapping rules and aggregation definitions.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AggregationRule(BaseModel):
    """Rule for how a field should be aggregated."""
    
    field_pattern: str = Field(..., description="Field name pattern (regex)")
    default_aggregation: str = Field(..., description="Default aggregation: sum, avg, count, min, max, count_distinct")
    
    # Business logic
    description: Optional[str] = Field(None, description="Why this aggregation is used")
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "field_pattern": ".*amount.*|.*revenue.*|.*price.*",
                    "default_aggregation": "sum",
                    "description": "Monetary fields should be summed"
                },
                {
                    "field_pattern": ".*count.*|.*quantity.*",
                    "default_aggregation": "sum",
                    "description": "Count fields should be summed"
                },
                {
                    "field_pattern": ".*rate.*|.*percentage.*",
                    "default_aggregation": "avg",
                    "description": "Rates should be averaged"
                }
            ]
        }


class FieldMappingRule(BaseModel):
    """Rule for mapping technical field names to business names."""
    
    # Pattern matching
    technical_pattern: str = Field(..., description="Technical field name pattern (regex)")
    
    # Business mapping
    business_name_template: str = Field(..., description="Business name template (can use capture groups)")
    description_template: Optional[str] = Field(None, description="Description template")
    
    # Synonyms
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    
    # Formatting
    format_string: Optional[str] = Field(None, description="Display format (e.g., $#,##0.00 for currency)")
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "technical_pattern": "(.*)_amount",
                    "business_name_template": "\\1 Amount",
                    "description_template": "Total \\1 amount in dollars",
                    "synonyms": ["\\1 total", "\\1 value"],
                    "format_string": "$#,##0.00"
                },
                {
                    "technical_pattern": "(.*)_count",
                    "business_name_template": "Number of \\1",
                    "description_template": "Count of \\1 records",
                    "synonyms": ["\\1 total", "\\1 quantity"]
                }
            ]
        }


class FieldMapping(BaseModel):
    """Complete mapping for a field."""
    
    # Connection details
    connection_id: Optional[str] = Field(None, description="Connection ID (for multi-tenant support)")
    
    # Technical details
    table_name: str = Field(..., description="Table name")
    column_name: str = Field(..., description="Technical column name")
    data_type: str = Field(..., description="Data type")
    
    # Business mapping
    display_name: str = Field(..., description="Business-friendly display name")
    description: str = Field(..., description="Field description")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names for search")
    
    # Aggregation
    is_measure: bool = Field(False, description="Is this a numeric measure")
    is_dimension: bool = Field(False, description="Is this a dimension/attribute")
    default_aggregation: Optional[str] = Field(None, description="Default aggregation function")
    
    # Formatting
    format_string: Optional[str] = Field(None, description="Display format")
    
    # AI-generated
    ai_generated: bool = Field(False, description="Was this mapping AI-generated")
    confidence_score: Optional[float] = Field(None, description="AI confidence score (0-1)")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    category: Optional[str] = Field(None, description="Business category (sales, finance, operations, etc.)")
