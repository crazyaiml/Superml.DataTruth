"""
API Request and Response Models

Pydantic models for API requests and responses.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


# User Context Models


class UserContextRequest(BaseModel):
    """User context for query personalization."""
    
    user_id: Optional[str] = Field(None, description="User identifier")
    role: Optional[str] = Field(None, description="User role")
    department: Optional[str] = Field(None, description="User department")
    permissions: Optional[Set[str]] = Field(None, description="User permissions")
    include_pending: bool = Field(False, description="Include pending transactions")
    use_estimated_costs: bool = Field(False, description="Use estimated costs")
    special_context: Optional[Dict[str, Any]] = Field(None, description="Special context")


# Request Models


class TimeRangeRequest(BaseModel):
    """Time range specification for queries."""

    start_date: Optional[date] = Field(None, description="Start date (inclusive)")
    end_date: Optional[date] = Field(None, description="End date (inclusive)")
    period: Optional[str] = Field(
        None,
        description="Relative period (e.g., 'last_quarter', 'this_year')",
        examples=["last_quarter", "this_year", "ytd"],
    )


class FilterRequest(BaseModel):
    """Filter condition for queries."""

    field: str = Field(description="Field name to filter on")
    operator: str = Field(
        description="Comparison operator",
        examples=["=", "!=", ">", ">=", "<", "<=", "in", "like"],
    )
    value: Any = Field(description="Value to compare against")


class NaturalLanguageQueryRequest(BaseModel):
    """Request for natural language query."""

    question: str = Field(
        description="Natural language question",
        examples=["What was the revenue last quarter by agent?"],
        min_length=1,
    )
    connection_id: Optional[str] = Field(
        None, description="Database connection ID to query against"
    )
    context: Optional[List[str]] = Field(
        None, description="Previous queries for follow-up context"
    )
    clarifications: Optional[Dict[str, Any]] = Field(
        None, description="Clarifications for ambiguous queries"
    )
    user_context: Optional[UserContextRequest] = Field(
        None, description="User context for personalization"
    )


class StructuredQueryRequest(BaseModel):
    """Request for structured query (QueryPlan)."""

    metric: str = Field(description="Metric to calculate")
    dimensions: List[str] = Field(
        default_factory=list, description="Dimensions to group by"
    )
    time_range: Optional[TimeRangeRequest] = Field(None, description="Time range filter")
    filters: List[FilterRequest] = Field(
        default_factory=list, description="Additional filters"
    )
    order_by: Dict[str, str] = Field(
        default_factory=dict, description="Sort order (field: asc/desc)"
    )
    limit: Optional[int] = Field(
        100, description="Maximum rows to return", ge=1, le=10000
    )


# Response Models


class QueryMetadata(BaseModel):
    """Metadata about query execution."""

    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    row_count: int = Field(description="Number of rows returned")
    from_cache: bool = Field(description="Whether result was from cache")
    generated_sql: Optional[str] = Field(None, description="Generated SQL query")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


class QueryResponse(BaseModel):
    """Response for query execution."""

    success: bool = Field(description="Whether query succeeded")
    data: List[Dict[str, Any]] = Field(description="Query result data")
    metadata: QueryMetadata = Field(description="Query execution metadata")
    error: Optional[str] = Field(None, description="Error message if failed")


class ClarificationResponse(BaseModel):
    """Response when query needs clarification."""

    needs_clarification: bool = Field(True, description="Indicates clarification needed")
    questions: List[str] = Field(description="Clarification questions")
    suggestions: Optional[Dict[str, List[str]]] = Field(
        None, description="Suggested values for clarifications"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status", examples=["healthy", "degraded"])
    database: str = Field(description="Database connection status")
    cache: str = Field(description="Cache connection status")
    timestamp: datetime = Field(default_factory=datetime.now)


class MetricsResponse(BaseModel):
    """Available metrics from semantic layer."""

    metrics: List[Dict[str, str]] = Field(description="List of available metrics")
    count: int = Field(description="Total number of metrics")


class DimensionsResponse(BaseModel):
    """Available dimensions from semantic layer."""

    dimensions: List[Dict[str, str]] = Field(
        description="List of available dimensions"
    )
    count: int = Field(description="Total number of dimensions")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now)


# Authentication Models


class TokenRequest(BaseModel):
    """API token request."""

    username: str = Field(description="Username", min_length=1)
    password: str = Field(description="Password", min_length=1)


class TokenResponse(BaseModel):
    """API token response."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiry in seconds")
