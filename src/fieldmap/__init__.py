"""
Field Mapping Module

Maps technical field names to business-friendly names and descriptions.
Similar to ThoughtSpot's field mapping and AI description generation.
"""

from src.fieldmap.mapper import FieldMapper, get_field_mapper
from src.fieldmap.models import (
    FieldMapping,
    FieldMappingRule,
    AggregationRule,
)
from src.fieldmap.ai_describer import AIFieldDescriber, get_ai_describer

__all__ = [
    "FieldMapper",
    "get_field_mapper",
    "FieldMapping",
    "FieldMappingRule",
    "AggregationRule",
    "AIFieldDescriber",
    "get_ai_describer",
]
