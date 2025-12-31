"""
RLS Configuration Loader

Loads user RLS configuration from database and creates UserContext for query execution.
"""

from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from src.user.authorization import (
    UserContext, Role, Permission, TablePermission, RLSFilter
)

logger = logging.getLogger(__name__)


async def load_user_rls_context(
    db: AsyncSession,
    user_id: int,
    connection_id: int
) -> UserContext:
    """
    Load complete UserContext from database including role, permissions, and RLS filters.
    
    Args:
        db: Database session
        user_id: User ID
        connection_id: Database connection ID
        
    Returns:
        UserContext with configured permissions and RLS filters
    """
    try:
        # Get user info
        user_query = await db.execute(
            text("SELECT username, email FROM users WHERE id = :user_id"),
            {'user_id': user_id}
        )
        user_row = user_query.fetchone()
        if not user_row:
            raise ValueError(f"User {user_id} not found")
        
        username = user_row[0]
        email = user_row[1]
        
        # Get user role for this connection
        role_query = await db.execute(
            text("""
                SELECT role FROM user_connection_roles
                WHERE user_id = :user_id AND connection_id = :connection_id AND is_active = TRUE
            """),
            {'user_id': user_id, 'connection_id': connection_id}
        )
        role_row = role_query.fetchone()
        role_str = role_row[0] if role_row else 'VIEWER'
        
        # Map string role to Role enum
        try:
            role = Role[role_str]
        except KeyError:
            logger.warning(f"Unknown role '{role_str}', defaulting to VIEWER")
            role = Role.VIEWER
        
        # Get RLS filters
        filters_query = await db.execute(
            text("""
                SELECT table_name, column_name, operator, filter_value
                FROM user_rls_filters
                WHERE user_id = :user_id AND connection_id = :connection_id AND is_active = TRUE
            """),
            {'user_id': user_id, 'connection_id': connection_id}
        )
        
        rls_filters = []
        for row in filters_query.fetchall():
            try:
                # Deserialize filter value
                filter_value = json.loads(row[3]) if row[3] else None
                
                rls_filters.append(RLSFilter(
                    table=row[0],
                    column=row[1],
                    operator=row[2],
                    value=filter_value
                ))
            except Exception as e:
                logger.error(f"Failed to parse RLS filter: {e}")
                continue
        
        # Get table permissions
        perms_query = await db.execute(
            text("""
                SELECT table_name, can_read, can_write, can_delete, allowed_columns, denied_columns
                FROM user_table_permissions
                WHERE user_id = :user_id AND connection_id = :connection_id AND is_active = TRUE
            """),
            {'user_id': user_id, 'connection_id': connection_id}
        )
        
        table_permissions = []
        for row in perms_query.fetchall():
            try:
                allowed_cols = json.loads(row[4]) if row[4] else None
                denied_cols = json.loads(row[5]) if row[5] else None
                
                table_permissions.append(TablePermission(
                    table=row[0],
                    allowed_columns=allowed_cols,
                    denied_columns=denied_cols
                ))
            except Exception as e:
                logger.error(f"Failed to parse table permission: {e}")
                continue
        
        # Determine permissions based on role
        permissions = []
        if role in [Role.ADMIN, Role.ANALYST]:
            permissions = [
                Permission.QUERY_DATA,
                Permission.VIEW_METRICS,
                Permission.VIEW_INSIGHTS
            ]
        elif role == Role.VIEWER:
            permissions = [
                Permission.QUERY_DATA,
                Permission.VIEW_METRICS
            ]
        else:  # EXTERNAL
            permissions = [Permission.QUERY_DATA]
        
        # Create UserContext
        user_context = UserContext(
            user_id=str(user_id),
            username=username,
            email=email,
            roles=[role],
            permissions=permissions,
            table_permissions=table_permissions if table_permissions else None,
            rls_filters=rls_filters if rls_filters else None
        )
        
        logger.info(f"Loaded RLS context for user {username}: role={role_str}, filters={len(rls_filters)}, permissions={len(table_permissions)}")
        
        return user_context
        
    except Exception as e:
        logger.error(f"Failed to load user RLS context: {e}")
        # Return minimal context with VIEWER role
        return UserContext(
            user_id=str(user_id),
            username="unknown",
            roles=[Role.VIEWER],
            permissions=[Permission.QUERY_DATA]
        )


async def load_user_context_for_api(
    db: AsyncSession,
    user_id: int,
    connection_id: int,
    enable_rls: bool = True
) -> Optional[UserContext]:
    """
    Load user context for API query execution.
    
    Args:
        db: Database session
        user_id: User ID
        connection_id: Database connection ID
        enable_rls: Whether to enable RLS (if False, returns None for default admin context)
        
    Returns:
        UserContext if enable_rls=True, None otherwise
    """
    if not enable_rls:
        return None
    
    return await load_user_rls_context(db, user_id, connection_id)


def get_rls_summary(user_context: UserContext) -> dict:
    """
    Get a summary of RLS configuration for display.
    
    Args:
        user_context: User context
        
    Returns:
        Dictionary with RLS summary
    """
    return {
        'user_id': user_context.user_id,
        'username': user_context.username,
        'roles': [r.value for r in user_context.roles],
        'is_admin': user_context.is_admin(),
        'rls_filters_count': len(user_context.rls_filters) if user_context.rls_filters else 0,
        'rls_filters': [
            {
                'table': f.table,
                'column': f.column,
                'operator': f.operator,
                'value': f.value
            }
            for f in (user_context.rls_filters or [])
        ],
        'table_permissions_count': len(user_context.table_permissions) if user_context.table_permissions else 0,
        'table_permissions': [
            {
                'table': p.table,
                'allowed_columns': p.allowed_columns,
                'denied_columns': p.denied_columns
            }
            for p in (user_context.table_permissions or [])
        ]
    }
