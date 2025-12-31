"""
User Management Module

Handles user profiles, roles, and goals.
"""

from src.user.models import (
    UserRole,
    UserProfile,
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserGoalSuggestions,
    ROLE_GOAL_SUGGESTIONS
)
from src.user.manager import UserManager, get_user_manager

__all__ = [
    'UserRole',
    'UserProfile',
    'CreateUserRequest',
    'UpdateUserRequest',
    'UserListResponse',
    'UserGoalSuggestions',
    'ROLE_GOAL_SUGGESTIONS',
    'UserManager',
    'get_user_manager'
]
