"""
User Management Models

Models for user profiles with roles and goals.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re
from enum import Enum


class UserRole(str, Enum):
    """User roles with different access levels and insight needs."""
    EXECUTIVE = "executive"
    MANAGER = "manager"
    ANALYST = "analyst"
    TRADER = "trader"
    INVESTOR = "investor"
    SALES = "sales"
    OPERATIONS = "operations"
    FINANCE = "finance"
    AGENT = "agent"
    ADMIN = "admin"


class UserProfile(BaseModel):
    """User profile with role and goals."""
    id: str = Field(description="Unique user identifier")
    username: str = Field(description="Username")
    email: str = Field(description="Email address")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format, allowing .local domains."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v
    full_name: str = Field(description="Full name")
    role: UserRole = Field(description="User role/persona")
    goals: List[str] = Field(default_factory=list, description="User's business goals")
    department: Optional[str] = Field(None, description="Department")
    preferences: dict = Field(default_factory=dict, description="User preferences")
    is_active: bool = Field(True, description="Is user active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateUserRequest(BaseModel):
    """Request to create a new user."""
    username: str = Field(description="Username", min_length=3, max_length=50)
    email: str = Field(description="Email address")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format, allowing .local domains."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v
    password: str = Field(description="Password", min_length=6)
    full_name: str = Field(description="Full name")
    role: UserRole = Field(description="User role")
    goals: List[str] = Field(default_factory=list, description="Business goals")
    department: Optional[str] = Field(None, description="Department")


class UpdateUserRequest(BaseModel):
    """Request to update user details."""
    email: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format, allowing .local domains."""
        if v is None:
            return v
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    goals: Optional[List[str]] = None
    department: Optional[str] = None
    preferences: Optional[dict] = None
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    """Response with list of users."""
    users: List[UserProfile]
    total: int


class UserGoalSuggestions(BaseModel):
    """Suggested goals by role."""
    role: UserRole
    suggested_goals: List[str]


# Role-based goal suggestions
ROLE_GOAL_SUGGESTIONS = {
    UserRole.EXECUTIVE: [
        "Drive strategic growth and profitability",
        "Monitor key business metrics and KPIs",
        "Identify market trends and opportunities",
        "Optimize resource allocation",
        "Assess business risks and mitigation strategies"
    ],
    UserRole.TRADER: [
        "Identify short-term trading opportunities",
        "Monitor market volatility and price movements",
        "Optimize trade execution timing",
        "Manage risk exposure",
        "Track portfolio performance real-time"
    ],
    UserRole.INVESTOR: [
        "Identify long-term investment opportunities",
        "Assess asset growth potential",
        "Diversify portfolio for risk management",
        "Monitor market trends and fundamentals",
        "Evaluate ROI and value creation"
    ],
    UserRole.ANALYST: [
        "Discover patterns and insights in data",
        "Ensure data quality and accuracy",
        "Build predictive models",
        "Conduct deep-dive analysis",
        "Generate actionable recommendations"
    ],
    UserRole.MANAGER: [
        "Improve team performance and productivity",
        "Track operational metrics",
        "Optimize resource utilization",
        "Identify bottlenecks and inefficiencies",
        "Drive process improvements"
    ],
    UserRole.SALES: [
        "Increase revenue and conversion rates",
        "Identify high-value prospects",
        "Optimize sales pipeline",
        "Track customer engagement",
        "Improve customer retention"
    ],
    UserRole.OPERATIONS: [
        "Improve operational efficiency",
        "Reduce costs and waste",
        "Ensure quality standards",
        "Optimize supply chain",
        "Monitor process performance"
    ],
    UserRole.FINANCE: [
        "Optimize budget allocation",
        "Track financial performance",
        "Forecast revenue and expenses",
        "Manage cash flow",
        "Ensure compliance and controls"
    ],
    UserRole.AGENT: [
        "Resolve customer issues quickly",
        "Improve response time",
        "Track task completion",
        "Meet service level agreements",
        "Enhance customer satisfaction"
    ],
    UserRole.ADMIN: [
        "Manage system configuration",
        "Monitor system health",
        "Ensure data security",
        "Manage user access",
        "Optimize system performance"
    ]
}
