"""
Authentication and Authorization

JWT-based authentication with API key support.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, ExpiredSignatureError, jwt

from src.config.settings import get_settings

settings = get_settings()
security = HTTPBearer()
logger = logging.getLogger(__name__)


# JWT Configuration
SECRET_KEY = settings.api_secret_key if hasattr(settings, 'api_secret_key') else secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiry duration

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify JWT token and extract payload.

    Args:
        token: JWT token string

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user with username and password.
    Uses user management database for authentication.

    Args:
        username: Username
        password: Password

    Returns:
        User dict if authenticated, None otherwise
    """
    logger.info(f"Attempting to authenticate user: {username}")
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        user_profile = manager.verify_password(username, password)
        
        if user_profile:
            logger.info(f"User {username} authenticated successfully with role {user_profile.role.value}")
            return {
                "user_id": user_profile.id,
                "username": user_profile.username,
                "role": user_profile.role.value,
                "full_name": user_profile.full_name,
                "email": user_profile.email,
                "department": user_profile.department,
                "goals": user_profile.goals,
                "permissions": {"admin"} if user_profile.role.value == "admin" else {"user"}
            }
        else:
            logger.warning(f"Authentication failed for user: {username} - invalid credentials")
    except Exception as e:
        logger.error(f"Error checking user management database: {e}", exc_info=True)
    
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User information

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = verify_token(token)

    username = payload.get("sub")
    
    # Get user from database
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        user_profile = manager.get_user_by_username(username)
        
        if user_profile and user_profile.is_active:
            return {
                "user_id": user_profile.id,
                "username": user_profile.username,
                "role": user_profile.role.value,
                "full_name": user_profile.full_name,
                "email": user_profile.email,
                "department": user_profile.department,
                "goals": user_profile.goals,
                "permissions": {"admin"} if user_profile.role.value == "admin" else {"user"}
            }
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found",
    )


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require admin role for endpoint access.

    Args:
        current_user: Current authenticated user

    Returns:
        User information

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
