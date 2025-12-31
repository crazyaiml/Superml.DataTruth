"""
RLS Configuration Management API

Provides endpoints for managing user-level RLS filters, roles, and permissions.
Allows administrators to configure fine-grained access control per user and connection.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user, require_role
from src.api.models import User
from src.database.connection import get_db
from src.user.authorization import Role as UserRole, RLSFilter
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rls", tags=["RLS Configuration"])


# Pydantic Models
class RLSFilterCreate(BaseModel):
    """Request model for creating RLS filter"""
    user_id: int = Field(..., description="User ID to apply filter to")
    connection_id: int = Field(..., description="Database connection ID")
    table_name: str = Field(..., description="Table name for the filter")
    column_name: str = Field(..., description="Column name for the filter")
    operator: str = Field(..., description="Filter operator (=, !=, IN, etc.)")
    filter_value: Any = Field(..., description="Filter value (string, number, or array)")
    
    @validator('operator')
    def validate_operator(cls, v):
        valid_operators = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'IS NULL', 'IS NOT NULL']
        if v not in valid_operators:
            raise ValueError(f'Operator must be one of: {", ".join(valid_operators)}')
        return v


class RLSFilterUpdate(BaseModel):
    """Request model for updating RLS filter"""
    operator: Optional[str] = None
    filter_value: Optional[Any] = None
    is_active: Optional[bool] = None
    
    @validator('operator')
    def validate_operator(cls, v):
        if v is not None:
            valid_operators = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'IS NULL', 'IS NOT NULL']
            if v not in valid_operators:
                raise ValueError(f'Operator must be one of: {", ".join(valid_operators)}')
        return v


class RLSFilterResponse(BaseModel):
    """Response model for RLS filter"""
    id: int
    user_id: int
    connection_id: int
    table_name: str
    column_name: str
    operator: str
    filter_value: Any
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]


class UserRoleCreate(BaseModel):
    """Request model for assigning user role"""
    user_id: int = Field(..., description="User ID")
    connection_id: int = Field(..., description="Database connection ID")
    role: str = Field(..., description="Role name (ADMIN, ANALYST, VIEWER, etc.)")
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['ADMIN', 'ANALYST', 'VIEWER', 'EXTERNAL', 'CUSTOM']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class UserRoleUpdate(BaseModel):
    """Request model for updating user role"""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            valid_roles = ['ADMIN', 'ANALYST', 'VIEWER', 'EXTERNAL', 'CUSTOM']
            if v not in valid_roles:
                raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class UserRoleResponse(BaseModel):
    """Response model for user role"""
    id: int
    user_id: int
    connection_id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]


class TablePermissionCreate(BaseModel):
    """Request model for creating table permission"""
    user_id: int
    connection_id: int
    table_name: str
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False
    allowed_columns: Optional[List[str]] = None
    denied_columns: Optional[List[str]] = None


class TablePermissionUpdate(BaseModel):
    """Request model for updating table permission"""
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None
    can_delete: Optional[bool] = None
    allowed_columns: Optional[List[str]] = None
    denied_columns: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TablePermissionResponse(BaseModel):
    """Response model for table permission"""
    id: int
    user_id: int
    connection_id: int
    table_name: str
    can_read: bool
    can_write: bool
    can_delete: bool
    allowed_columns: Optional[List[str]]
    denied_columns: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserRLSConfigResponse(BaseModel):
    """Complete RLS configuration for a user"""
    user_id: int
    username: str
    connection_id: int
    role: Optional[str]
    rls_filters: List[RLSFilterResponse]
    table_permissions: List[TablePermissionResponse]


# Helper Functions
def serialize_filter_value(value: Any) -> str:
    """Serialize filter value to JSON string"""
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    elif isinstance(value, str):
        return json.dumps(value)
    else:
        return json.dumps(value)


def deserialize_filter_value(value: str) -> Any:
    """Deserialize filter value from JSON string"""
    try:
        return json.loads(value)
    except:
        return value


async def log_audit(
    db: AsyncSession,
    user_id: int,
    connection_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    old_value: Optional[Dict] = None,
    new_value: Optional[Dict] = None,
    performed_by: int = None,
    request: Request = None
):
    """Log RLS configuration change to audit table"""
    try:
        ip_address = request.client.host if request else None
        user_agent = request.headers.get('user-agent') if request else None
        
        query = text("""
            INSERT INTO rls_configuration_audit 
            (user_id, connection_id, action, entity_type, entity_id, old_value, new_value, performed_by, ip_address, user_agent)
            VALUES (:user_id, :connection_id, :action, :entity_type, :entity_id, :old_value, :new_value, :performed_by, :ip_address, :user_agent)
        """)
        
        await db.execute(query, {
            'user_id': user_id,
            'connection_id': connection_id,
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_value': json.dumps(old_value) if old_value else None,
            'new_value': json.dumps(new_value) if new_value else None,
            'performed_by': performed_by,
            'ip_address': ip_address,
            'user_agent': user_agent
        })
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


# RLS Filter Endpoints
@router.post("/filters", response_model=RLSFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_rls_filter(
    filter_data: RLSFilterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(['ADMIN'])),
    request: Request = None
):
    """
    Create a new RLS filter for a user.
    
    Only administrators can create RLS filters.
    """
    try:
        # Serialize filter value
        filter_value_json = serialize_filter_value(filter_data.filter_value)
        
        # Insert filter
        query = text("""
            INSERT INTO user_rls_filters 
            (user_id, connection_id, table_name, column_name, operator, filter_value, created_by)
            VALUES (:user_id, :connection_id, :table_name, :column_name, :operator, :filter_value, :created_by)
            ON CONFLICT (user_id, connection_id, table_name, column_name) 
            DO UPDATE SET 
                operator = EXCLUDED.operator,
                filter_value = EXCLUDED.filter_value,
                updated_at = CURRENT_TIMESTAMP,
                is_active = TRUE
            RETURNING id, user_id, connection_id, table_name, column_name, operator, filter_value, 
                      is_active, created_at, updated_at, created_by
        """)
        
        result = await db.execute(query, {
            'user_id': filter_data.user_id,
            'connection_id': filter_data.connection_id,
            'table_name': filter_data.table_name,
            'column_name': filter_data.column_name,
            'operator': filter_data.operator,
            'filter_value': filter_value_json,
            'created_by': current_user.id
        })
        await db.commit()
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create RLS filter")
        
        # Log audit
        await log_audit(
            db, filter_data.user_id, filter_data.connection_id,
            'CREATE', 'RLS_FILTER', row[0],
            new_value=filter_data.dict(),
            performed_by=current_user.id,
            request=request
        )
        
        return RLSFilterResponse(
            id=row[0],
            user_id=row[1],
            connection_id=row[2],
            table_name=row[3],
            column_name=row[4],
            operator=row[5],
            filter_value=deserialize_filter_value(row[6]),
            is_active=row[7],
            created_at=row[8],
            updated_at=row[9],
            created_by=row[10]
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating RLS filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters/user/{user_id}/connection/{connection_id}", response_model=List[RLSFilterResponse])
async def get_user_rls_filters(
    user_id: int,
    connection_id: int,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all RLS filters for a specific user and connection.
    
    Users can view their own filters. Admins can view any user's filters.
    """
    # Check permission
    if current_user.id != user_id and 'ADMIN' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's filters")
    
    try:
        query_str = """
            SELECT id, user_id, connection_id, table_name, column_name, operator, filter_value,
                   is_active, created_at, updated_at, created_by
            FROM user_rls_filters
            WHERE user_id = :user_id AND connection_id = :connection_id
        """
        
        if not include_inactive:
            query_str += " AND is_active = TRUE"
        
        query_str += " ORDER BY table_name, column_name"
        
        result = await db.execute(text(query_str), {
            'user_id': user_id,
            'connection_id': connection_id
        })
        
        filters = []
        for row in result.fetchall():
            filters.append(RLSFilterResponse(
                id=row[0],
                user_id=row[1],
                connection_id=row[2],
                table_name=row[3],
                column_name=row[4],
                operator=row[5],
                filter_value=deserialize_filter_value(row[6]),
                is_active=row[7],
                created_at=row[8],
                updated_at=row[9],
                created_by=row[10]
            ))
        
        return filters
    except Exception as e:
        logger.error(f"Error fetching RLS filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/filters/{filter_id}", response_model=RLSFilterResponse)
async def update_rls_filter(
    filter_id: int,
    filter_data: RLSFilterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(['ADMIN'])),
    request: Request = None
):
    """
    Update an existing RLS filter.
    
    Only administrators can update RLS filters.
    """
    try:
        # Get existing filter
        existing = await db.execute(
            text("SELECT * FROM user_rls_filters WHERE id = :id"),
            {'id': filter_id}
        )
        existing_row = existing.fetchone()
        if not existing_row:
            raise HTTPException(status_code=404, detail="RLS filter not found")
        
        # Build update query
        updates = []
        params = {'id': filter_id}
        
        if filter_data.operator is not None:
            updates.append("operator = :operator")
            params['operator'] = filter_data.operator
        
        if filter_data.filter_value is not None:
            updates.append("filter_value = :filter_value")
            params['filter_value'] = serialize_filter_value(filter_data.filter_value)
        
        if filter_data.is_active is not None:
            updates.append("is_active = :is_active")
            params['is_active'] = filter_data.is_active
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = text(f"""
            UPDATE user_rls_filters
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, user_id, connection_id, table_name, column_name, operator, filter_value,
                      is_active, created_at, updated_at, created_by
        """)
        
        result = await db.execute(query, params)
        await db.commit()
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to update RLS filter")
        
        # Log audit
        await log_audit(
            db, row[1], row[2],
            'UPDATE', 'RLS_FILTER', filter_id,
            old_value={'id': filter_id},
            new_value=filter_data.dict(exclude_none=True),
            performed_by=current_user.id,
            request=request
        )
        
        return RLSFilterResponse(
            id=row[0],
            user_id=row[1],
            connection_id=row[2],
            table_name=row[3],
            column_name=row[4],
            operator=row[5],
            filter_value=deserialize_filter_value(row[6]),
            is_active=row[7],
            created_at=row[8],
            updated_at=row[9],
            created_by=row[10]
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating RLS filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/filters/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rls_filter(
    filter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(['ADMIN'])),
    request: Request = None
):
    """
    Delete an RLS filter.
    
    Only administrators can delete RLS filters.
    """
    try:
        # Get existing filter for audit log
        existing = await db.execute(
            text("SELECT user_id, connection_id FROM user_rls_filters WHERE id = :id"),
            {'id': filter_id}
        )
        existing_row = existing.fetchone()
        if not existing_row:
            raise HTTPException(status_code=404, detail="RLS filter not found")
        
        # Delete filter
        await db.execute(
            text("DELETE FROM user_rls_filters WHERE id = :id"),
            {'id': filter_id}
        )
        await db.commit()
        
        # Log audit
        await log_audit(
            db, existing_row[0], existing_row[1],
            'DELETE', 'RLS_FILTER', filter_id,
            old_value={'id': filter_id},
            performed_by=current_user.id,
            request=request
        )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting RLS filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Role Endpoints
@router.post("/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_user_role(
    role_data: UserRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(['ADMIN'])),
    request: Request = None
):
    """
    Assign a role to a user for a specific connection.
    
    Only administrators can assign roles.
    """
    try:
        query = text("""
            INSERT INTO user_connection_roles (user_id, connection_id, role, created_by)
            VALUES (:user_id, :connection_id, :role, :created_by)
            ON CONFLICT (user_id, connection_id)
            DO UPDATE SET 
                role = EXCLUDED.role,
                updated_at = CURRENT_TIMESTAMP,
                is_active = TRUE
            RETURNING id, user_id, connection_id, role, is_active, created_at, updated_at, created_by
        """)
        
        result = await db.execute(query, {
            'user_id': role_data.user_id,
            'connection_id': role_data.connection_id,
            'role': role_data.role,
            'created_by': current_user.id
        })
        await db.commit()
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to assign role")
        
        # Log audit
        await log_audit(
            db, role_data.user_id, role_data.connection_id,
            'CREATE', 'ROLE', row[0],
            new_value=role_data.dict(),
            performed_by=current_user.id,
            request=request
        )
        
        return UserRoleResponse(
            id=row[0],
            user_id=row[1],
            connection_id=row[2],
            role=row[3],
            is_active=row[4],
            created_at=row[5],
            updated_at=row[6],
            created_by=row[7]
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error assigning role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles/user/{user_id}", response_model=List[UserRoleResponse])
async def get_user_roles(
    user_id: int,
    connection_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get roles for a user across all connections or a specific connection.
    
    Users can view their own roles. Admins can view any user's roles.
    """
    if current_user.id != user_id and 'ADMIN' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's roles")
    
    try:
        query_str = """
            SELECT id, user_id, connection_id, role, is_active, created_at, updated_at, created_by
            FROM user_connection_roles
            WHERE user_id = :user_id AND is_active = TRUE
        """
        params = {'user_id': user_id}
        
        if connection_id is not None:
            query_str += " AND connection_id = :connection_id"
            params['connection_id'] = connection_id
        
        result = await db.execute(text(query_str), params)
        
        roles = []
        for row in result.fetchall():
            roles.append(UserRoleResponse(
                id=row[0],
                user_id=row[1],
                connection_id=row[2],
                role=row[3],
                is_active=row[4],
                created_at=row[5],
                updated_at=row[6],
                created_by=row[7]
            ))
        
        return roles
    except Exception as e:
        logger.error(f"Error fetching user roles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get complete RLS configuration for a user
@router.get("/config/user/{user_id}/connection/{connection_id}", response_model=UserRLSConfigResponse)
async def get_user_rls_config(
    user_id: int,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete RLS configuration for a user including role, filters, and permissions.
    
    This is the primary endpoint for loading user RLS configuration during query execution.
    """
    if current_user.id != user_id and 'ADMIN' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's configuration")
    
    try:
        # Get user info
        user_query = await db.execute(
            text("SELECT username FROM users WHERE id = :user_id"),
            {'user_id': user_id}
        )
        user_row = user_query.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get role
        role_query = await db.execute(
            text("""
                SELECT role FROM user_connection_roles 
                WHERE user_id = :user_id AND connection_id = :connection_id AND is_active = TRUE
            """),
            {'user_id': user_id, 'connection_id': connection_id}
        )
        role_row = role_query.fetchone()
        role = role_row[0] if role_row else None
        
        # Get filters
        filters = await get_user_rls_filters(user_id, connection_id, False, db, current_user)
        
        # Get table permissions
        perms_query = await db.execute(
            text("""
                SELECT id, user_id, connection_id, table_name, can_read, can_write, can_delete,
                       allowed_columns, denied_columns, is_active, created_at, updated_at
                FROM user_table_permissions
                WHERE user_id = :user_id AND connection_id = :connection_id AND is_active = TRUE
            """),
            {'user_id': user_id, 'connection_id': connection_id}
        )
        
        table_permissions = []
        for row in perms_query.fetchall():
            table_permissions.append(TablePermissionResponse(
                id=row[0],
                user_id=row[1],
                connection_id=row[2],
                table_name=row[3],
                can_read=row[4],
                can_write=row[5],
                can_delete=row[6],
                allowed_columns=json.loads(row[7]) if row[7] else None,
                denied_columns=json.loads(row[8]) if row[8] else None,
                is_active=row[9],
                created_at=row[10],
                updated_at=row[11]
            ))
        
        return UserRLSConfigResponse(
            user_id=user_id,
            username=user_row[0],
            connection_id=connection_id,
            role=role,
            rls_filters=filters,
            table_permissions=table_permissions
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching RLS configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
