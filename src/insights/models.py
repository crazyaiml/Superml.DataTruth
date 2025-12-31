"""
Insight Models

Data models for automated insights.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles/personas with different insight needs."""
    EXECUTIVE = "executive"  # C-level, Directors - strategic KPIs, long-term trends
    MANAGER = "manager"  # Department heads - operational metrics, team performance
    ANALYST = "analyst"  # Data analysts - detailed patterns, data quality, deep dives
    TRADER = "trader"  # Traders - short-term volatility, real-time patterns, quick actions
    INVESTOR = "investor"  # Investors - long-term trends, growth, risk assessment
    SALES = "sales"  # Sales team - revenue metrics, customer insights, conversion
    OPERATIONS = "operations"  # Operations team - efficiency, bottlenecks, quality
    FINANCE = "finance"  # Finance team - cost analysis, budgets, forecasts
    AGENT = "agent"  # Front-line agents - task-specific, actionable insights


class InsightType(str, Enum):
    """Types of insights that can be generated."""
    PATTERN = "pattern"  # Detected patterns in data
    ANOMALY = "anomaly"  # Anomalies and outliers
    TREND = "trend"  # Trends over time
    COMPARISON = "comparison"  # Comparisons between entities
    ATTRIBUTION = "attribution"  # Attribution analysis (what drives metrics)
    FORECAST = "forecast"  # Predictions and forecasts
    PERFORMANCE = "performance"  # Performance metrics
    QUALITY = "quality"  # Data quality insights
    USAGE = "usage"  # Usage patterns


class InsightSeverity(str, Enum):
    """Severity level of an insight."""
    INFO = "info"  # Informational
    LOW = "low"  # Low priority
    MEDIUM = "medium"  # Medium priority
    HIGH = "high"  # High priority
    CRITICAL = "critical"  # Critical issue


class Insight(BaseModel):
    """Single insight generated from analysis."""
    id: str = Field(description="Unique insight identifier")
    type: InsightType = Field(description="Type of insight")
    severity: InsightSeverity = Field(description="Severity level")
    title: str = Field(description="Insight title")
    description: str = Field(description="Detailed description")
    facts: List[str] = Field(description="Facts supporting this insight (no opinions)")
    metric_value: Optional[float] = Field(None, description="Primary metric value")
    metric_label: Optional[str] = Field(None, description="Metric label")
    change_percent: Optional[float] = Field(None, description="Percentage change")
    confidence: float = Field(description="Confidence score (0-1)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When generated")
    data: Optional[Dict[str, Any]] = Field(None, description="Supporting data")
    # Augmented insights enhancements
    forecast_data: Optional[Dict[str, Any]] = Field(None, description="Forecast predictions if applicable")
    attribution_data: Optional[Dict[str, Any]] = Field(None, description="Attribution analysis if applicable")
    impact_score: Optional[float] = Field(None, description="Impact score (0-1)")
    impact_level: Optional[str] = Field(None, description="Impact level: high, medium, low")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class InsightCard(BaseModel):
    """Insight card for UI display."""
    insight: Insight = Field(description="The insight")
    narrative: str = Field(description="LLM-generated narrative explanation")
    suggested_actions: List[str] = Field(description="Suggested actions based on insight")
    related_insights: List[str] = Field(default_factory=list, description="Related insight IDs")
    # Engagement tracking
    view_count: int = Field(0, description="Number of times viewed")
    engagement_rate: float = Field(0.0, description="User engagement rate (0-1)")


class InsightsRequest(BaseModel):
    """Request for generating insights."""
    connection_id: str = Field(description="Database connection ID")
    user_role: Optional[UserRole] = Field(None, description="User role/persona for tailored insights")
    insight_types: Optional[List[InsightType]] = Field(None, description="Types of insights to generate (all if not specified)")
    time_range_days: int = Field(7, description="Time range for analysis in days")
    max_insights: int = Field(10, description="Maximum number of insights to return")
    min_confidence: float = Field(0.6, description="Minimum confidence threshold")


class InsightsResponse(BaseModel):
    """Response containing generated insights."""
    connection_id: str = Field(description="Database connection ID")
    connection_name: str = Field(description="Database connection name")
    insights: List[InsightCard] = Field(description="Generated insight cards")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When generated")
    analysis_summary: str = Field(description="Overall analysis summary")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
