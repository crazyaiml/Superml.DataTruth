"""
Semantic Layer - Data Models

Pydantic models for metrics, dimensions, and joins defined in YAML files.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AggregationType(str, Enum):
    """Types of aggregation for metrics."""

    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    MIN = "min"
    MAX = "max"
    CALCULATED = "calculated"


class DataType(str, Enum):
    """Data types for metrics and dimensions."""

    INTEGER = "integer"
    DECIMAL = "decimal"
    STRING = "string"
    DATE = "date"
    BOOLEAN = "boolean"


class FormatType(str, Enum):
    """Format types for displaying values."""

    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    NUMBER = "number"


class Filter(BaseModel):
    """Filter condition for metrics."""

    field: str
    operator: str
    value: str | int | float | bool


class MetricFormat(BaseModel):
    """Formatting configuration for metrics."""

    type: FormatType
    currency: Optional[str] = None
    decimals: int = 2


class Metric(BaseModel):
    """Metric definition from semantic layer."""

    name: str
    display_name: str
    description: str
    formula: str
    base_table: str
    aggregation: AggregationType
    data_type: DataType
    filters: List[Filter] = Field(default_factory=list)
    format: MetricFormat
    synonyms: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    requires_time_comparison: bool = False

    def matches_name(self, name: str) -> bool:
        """Check if given name matches this metric (including synonyms)."""
        name_lower = name.lower().replace("_", " ").replace("-", " ")
        metric_name = self.name.lower().replace("_", " ")
        
        if name_lower == metric_name:
            return True
        
        return any(
            name_lower == syn.lower().replace("_", " ").replace("-", " ")
            for syn in self.synonyms
        )


class DimensionAttribute(BaseModel):
    """Attribute of a dimension."""

    name: str
    field: str
    data_type: DataType


class DimensionType(str, Enum):
    """Types of dimensions."""

    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"


class Dimension(BaseModel):
    """Dimension definition from semantic layer."""

    name: str
    display_name: str
    description: str
    table: Optional[str] = None
    field: Optional[str] = None
    primary_key: Optional[str] = None
    name_field: Optional[str] = None
    type: DimensionType
    attributes: List[DimensionAttribute] = Field(default_factory=list)
    default_display: str
    time_granularities: List[str] = Field(default_factory=list)
    possible_values: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    derived: bool = False

    def matches_name(self, name: str) -> bool:
        """Check if given name matches this dimension (including synonyms)."""
        name_lower = name.lower().replace("_", " ").replace("-", " ")
        dim_name = self.name.lower().replace("_", " ")
        
        if name_lower == dim_name:
            return True
        
        return any(
            name_lower == syn.lower().replace("_", " ").replace("-", " ")
            for syn in self.synonyms
        )


class JoinType(str, Enum):
    """SQL join types."""

    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"


class JoinCardinality(str, Enum):
    """Cardinality of join relationships."""

    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class JoinCondition(BaseModel):
    """Join condition between two fields."""

    from_field: str
    to_field: str


class Join(BaseModel):
    """Join relationship definition."""

    name: str
    from_table: str
    to_table: str
    join_type: JoinType
    on: List[JoinCondition]
    cardinality: JoinCardinality
    required: bool = False


class JoinPreference(BaseModel):
    """Join preference for specific scenarios."""

    scenario: str
    prefer: str
    over: str
    reason: str


class SemanticLayer(BaseModel):
    """Complete semantic layer definition."""

    metrics: Dict[str, Metric] = Field(default_factory=dict)
    dimensions: Dict[str, Dimension] = Field(default_factory=dict)
    joins: List[Join] = Field(default_factory=list)
    join_preferences: List[JoinPreference] = Field(default_factory=list)
    synonyms: Dict[str, Any] = Field(default_factory=dict)

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name or synonym."""
        # Direct lookup
        if name in self.metrics:
            return self.metrics[name]
        
        # Search by synonym
        for metric in self.metrics.values():
            if metric.matches_name(name):
                return metric
        
        return None

    def get_dimension(self, name: str) -> Optional[Dimension]:
        """Get dimension by name or synonym."""
        # Direct lookup
        if name in self.dimensions:
            return self.dimensions[name]
        
        # Search by synonym
        for dimension in self.dimensions.values():
            if dimension.matches_name(name):
                return dimension
        
        return None

    def get_join(self, from_table: str, to_table: str) -> Optional[Join]:
        """Get join between two tables."""
        for join in self.joins:
            if join.from_table == from_table and join.to_table == to_table:
                return join
        return None

    def list_metric_names(self) -> List[str]:
        """List all metric names including synonyms."""
        names = []
        for metric in self.metrics.values():
            names.append(metric.name)
            names.extend(metric.synonyms)
        return names

    def list_dimension_names(self) -> List[str]:
        """List all dimension names including synonyms."""
        names = []
        for dimension in self.dimensions.values():
            names.append(dimension.name)
            names.extend(dimension.synonyms)
        return names
