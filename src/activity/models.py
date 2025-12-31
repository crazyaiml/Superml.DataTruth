"""
Activity Tracking Models

Data models for user activity and query patterns.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ActivityType(str, Enum):
    """Types of user activities to track."""
    QUERY = "query"
    CHAT = "chat"
    SUGGESTION_CLICK = "suggestion_click"
    FEEDBACK = "feedback"


class UserActivity(BaseModel):
    """Model for user activity log entry."""
    id: Optional[int] = None
    user_id: str = Field(description="User identifier")
    activity_type: ActivityType = Field(description="Type of activity")
    query_text: Optional[str] = Field(None, description="User's query or chat message")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Full response with SQL, results, metadata")
    suggestion_clicked: Optional[str] = Field(None, description="Which suggestion was clicked")
    feedback_rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LogActivityRequest(BaseModel):
    """Request to log a user activity."""
    activity_type: ActivityType
    query_text: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    suggestion_clicked: Optional[str] = None
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[Dict[str, Any]] = None


class QueryPattern(BaseModel):
    """Model for learned query patterns."""
    id: Optional[int] = None
    pattern_type: str = Field(description="role_based, user_specific, or global")
    target_id: Optional[str] = Field(None, description="user_id or role name")
    query_template: str = Field(description="Template query with placeholders")
    frequency: int = Field(default=1, description="How often pattern appears")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Success rate 0-1")
    avg_response_time: Optional[float] = Field(None, description="Avg response time in seconds")
    last_used: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SuggestionPreferences(BaseModel):
    """User preferences for query suggestions."""
    user_id: str
    preferred_query_types: List[str] = Field(default_factory=list, description="Preferred types")
    excluded_metrics: List[str] = Field(default_factory=list, description="Metrics to exclude")
    preferred_metrics: List[str] = Field(default_factory=list, description="Metrics to prioritize")
    preferred_dimensions: List[str] = Field(default_factory=list, description="Dimensions to prioritize")
    show_advanced_queries: bool = Field(False, description="Show complex queries")
    max_suggestions: int = Field(6, ge=1, le=12, description="Number of suggestions")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PersonalizedSuggestions(BaseModel):
    """Response with personalized query suggestions."""
    suggestions: List[Dict[str, str]]
    source: str = Field(description="cached, learned, or llm_generated")
    user_patterns: Optional[List[str]] = Field(None, description="User's common patterns")
    role_patterns: Optional[List[str]] = Field(None, description="Role-based patterns")
