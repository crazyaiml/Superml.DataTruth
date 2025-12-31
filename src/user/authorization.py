"""
User Context and Authorization Framework

Implements user permissions, roles, and authorization for secure query execution.
Based on ThoughtSpot/enterprise BI security patterns.
"""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class Role(str, Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"              # Full access
    ANALYST = "analyst"          # Query + explore data
    VIEWER = "viewer"            # View dashboards only
    DATA_ENGINEER = "data_engineer"  # Manage semantic layer
    GUEST = "guest"              # Limited access


class Permission(str, Enum):
    """Granular permissions."""
    # Query permissions
    QUERY_DATA = "query_data"
    VIEW_DATA = "view_data"
    
    # Semantic layer permissions
    VIEW_METRICS = "view_metrics"
    CREATE_METRICS = "create_metrics"
    EDIT_METRICS = "edit_metrics"
    DELETE_METRICS = "delete_metrics"
    
    # Table/column permissions
    ACCESS_TABLE = "access_table"
    ACCESS_COLUMN = "access_column"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_RLS = "manage_rls"
    VIEW_AUDIT_LOGS = "view_audit_logs"


# Role hierarchy with default permissions
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.QUERY_DATA,
        Permission.VIEW_DATA,
        Permission.VIEW_METRICS,
        Permission.CREATE_METRICS,
        Permission.EDIT_METRICS,
        Permission.DELETE_METRICS,
        Permission.ACCESS_TABLE,
        Permission.ACCESS_COLUMN,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_RLS,
        Permission.VIEW_AUDIT_LOGS,
    },
    Role.ANALYST: {
        Permission.QUERY_DATA,
        Permission.VIEW_DATA,
        Permission.VIEW_METRICS,
        Permission.CREATE_METRICS,
        Permission.ACCESS_TABLE,
        Permission.ACCESS_COLUMN,
    },
    Role.VIEWER: {
        Permission.VIEW_DATA,
        Permission.VIEW_METRICS,
    },
    Role.DATA_ENGINEER: {
        Permission.QUERY_DATA,
        Permission.VIEW_DATA,
        Permission.VIEW_METRICS,
        Permission.CREATE_METRICS,
        Permission.EDIT_METRICS,
        Permission.DELETE_METRICS,
        Permission.ACCESS_TABLE,
        Permission.ACCESS_COLUMN,
    },
    Role.GUEST: {
        Permission.VIEW_DATA,
    }
}


class TablePermission(BaseModel):
    """Permission to access a specific table."""
    table_name: str = Field(description="Table name")
    can_query: bool = Field(default=False, description="Can query this table")
    can_view: bool = Field(default=False, description="Can view this table in UI")
    allowed_columns: Optional[List[str]] = Field(default=None, description="Specific columns allowed (None = all)")
    denied_columns: Optional[List[str]] = Field(default=None, description="Specific columns denied")


class RLSFilter(BaseModel):
    """Row-level security filter for a table."""
    table_name: str = Field(description="Table name")
    filter_condition: str = Field(description="SQL WHERE clause (without WHERE keyword)")
    description: Optional[str] = Field(default=None, description="Human-readable description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "orders",
                "filter_condition": "region = 'US' AND order_date >= '2024-01-01'",
                "description": "US orders from 2024 onwards"
            }
        }


class MetricPermission(BaseModel):
    """Permission to access specific metrics."""
    metric_name: str = Field(description="Metric name")
    can_view: bool = Field(default=True, description="Can view metric definition")
    can_query: bool = Field(default=True, description="Can query metric")


class UserContext(BaseModel):
    """
    Complete user context for authorization.
    
    Passed through entire query pipeline to enforce permissions.
    """
    user_id: str = Field(description="Unique user identifier")
    username: str = Field(description="Username")
    email: Optional[str] = Field(default=None, description="User email")
    
    # Roles and permissions
    roles: List[Role] = Field(description="User roles")
    custom_permissions: Set[Permission] = Field(default_factory=set, description="Additional permissions")
    
    # Table-level permissions
    table_permissions: List[TablePermission] = Field(default_factory=list, description="Table access rules")
    
    # Row-level security
    rls_filters: List[RLSFilter] = Field(default_factory=list, description="Row-level security filters")
    
    # Metric permissions
    metric_permissions: List[MetricPermission] = Field(default_factory=list, description="Metric access rules")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Context creation time")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        # Check custom permissions first
        if permission in self.custom_permissions:
            return True
        
        # Check role-based permissions
        for role in self.roles:
            if permission in ROLE_PERMISSIONS.get(role, set()):
                return True
        
        return False
    
    def can_access_table(self, table_name: str) -> bool:
        """Check if user can access a table."""
        if not self.has_permission(Permission.ACCESS_TABLE):
            return False
        
        # If no specific table permissions, deny by default
        if not self.table_permissions:
            return False
        
        # Check table-specific permissions
        for perm in self.table_permissions:
            if perm.table_name == table_name:
                return perm.can_query or perm.can_view
        
        return False
    
    def can_access_column(self, table_name: str, column_name: str) -> bool:
        """Check if user can access a specific column."""
        if not self.can_access_table(table_name):
            return False
        
        # Find table permission
        for perm in self.table_permissions:
            if perm.table_name == table_name:
                # Check denied columns
                if perm.denied_columns and column_name in perm.denied_columns:
                    return False
                
                # Check allowed columns
                if perm.allowed_columns is not None:
                    return column_name in perm.allowed_columns
                
                # If no specific column restrictions, allow
                return True
        
        return False
    
    def can_access_metric(self, metric_name: str) -> bool:
        """Check if user can access a metric."""
        if not self.has_permission(Permission.VIEW_METRICS):
            return False
        
        # If no specific metric permissions, allow by default
        if not self.metric_permissions:
            return True
        
        # Check metric-specific permissions
        for perm in self.metric_permissions:
            if perm.metric_name == metric_name:
                return perm.can_query
        
        return True
    
    def get_rls_filters_for_table(self, table_name: str) -> List[str]:
        """Get all RLS filter conditions for a table."""
        return [
            f.filter_condition
            for f in self.rls_filters
            if f.table_name == table_name
        ]
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return Role.ADMIN in self.roles


class AuthorizationCache:
    """
    Cache for authorization checks to avoid repeated lookups.
    
    Critical for performance in high-volume query scenarios.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
    
    def _make_key(self, user_id: str, resource_type: str, resource_name: str) -> str:
        """Generate cache key."""
        return f"{user_id}:{resource_type}:{resource_name}"
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self._timestamps:
            return True
        
        age = (datetime.utcnow() - self._timestamps[key]).total_seconds()
        return age > self.ttl_seconds
    
    def get(self, user_id: str, resource_type: str, resource_name: str) -> Optional[bool]:
        """Get cached authorization result."""
        key = self._make_key(user_id, resource_type, resource_name)
        
        if key in self._cache and not self._is_expired(key):
            return self._cache[key]
        
        return None
    
    def set(self, user_id: str, resource_type: str, resource_name: str, allowed: bool):
        """Cache authorization result."""
        key = self._make_key(user_id, resource_type, resource_name)
        self._cache[key] = allowed
        self._timestamps[key] = datetime.utcnow()
    
    def invalidate(self, user_id: Optional[str] = None):
        """Invalidate cache entries."""
        if user_id:
            # Invalidate all entries for a specific user
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
                del self._timestamps[key]
        else:
            # Invalidate entire cache
            self._cache.clear()
            self._timestamps.clear()
    
    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)


class AuthorizationValidator:
    """
    Validates user authorization for various resources.
    
    Central authorization enforcement point.
    """
    
    def __init__(self, enable_cache: bool = True):
        """
        Initialize validator.
        
        Args:
            enable_cache: Enable authorization caching
        """
        self.cache = AuthorizationCache() if enable_cache else None
    
    def validate_table_access(
        self,
        user: UserContext,
        table_name: str,
        operation: str = "query"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate user can access a table.
        
        Args:
            user: User context
            table_name: Table to access
            operation: Operation type (query, view)
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(user.user_id, "table", table_name)
            if cached is not None:
                return cached, None if cached else f"Access denied to table: {table_name}"
        
        # Check permission
        allowed = user.can_access_table(table_name)
        
        # Cache result
        if self.cache:
            self.cache.set(user.user_id, "table", table_name, allowed)
        
        if not allowed:
            return False, f"User {user.username} does not have access to table: {table_name}"
        
        return True, None
    
    def validate_column_access(
        self,
        user: UserContext,
        table_name: str,
        column_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate user can access a column.
        
        Args:
            user: User context
            table_name: Table name
            column_name: Column name
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check cache
        cache_key = f"{table_name}.{column_name}"
        if self.cache:
            cached = self.cache.get(user.user_id, "column", cache_key)
            if cached is not None:
                return cached, None if cached else f"Access denied to column: {table_name}.{column_name}"
        
        # Check permission
        allowed = user.can_access_column(table_name, column_name)
        
        # Cache result
        if self.cache:
            self.cache.set(user.user_id, "column", cache_key, allowed)
        
        if not allowed:
            return False, f"User {user.username} does not have access to column: {table_name}.{column_name}"
        
        return True, None
    
    def validate_metric_access(
        self,
        user: UserContext,
        metric_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate user can access a metric.
        
        Args:
            user: User context
            metric_name: Metric name
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check cache
        if self.cache:
            cached = self.cache.get(user.user_id, "metric", metric_name)
            if cached is not None:
                return cached, None if cached else f"Access denied to metric: {metric_name}"
        
        # Check permission
        allowed = user.can_access_metric(metric_name)
        
        # Cache result
        if self.cache:
            self.cache.set(user.user_id, "metric", metric_name, allowed)
        
        if not allowed:
            return False, f"User {user.username} does not have access to metric: {metric_name}"
        
        return True, None
    
    def validate_query_permission(self, user: UserContext) -> tuple[bool, Optional[str]]:
        """
        Validate user can execute queries.
        
        Args:
            user: User context
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        if not user.has_permission(Permission.QUERY_DATA):
            return False, f"User {user.username} does not have permission to query data"
        
        return True, None
    
    def invalidate_cache(self, user_id: Optional[str] = None):
        """Invalidate authorization cache."""
        if self.cache:
            self.cache.invalidate(user_id)


# Global singleton instances
_authorization_validator: Optional[AuthorizationValidator] = None


def get_authorization_validator() -> AuthorizationValidator:
    """Get global authorization validator instance."""
    global _authorization_validator
    if _authorization_validator is None:
        _authorization_validator = AuthorizationValidator(enable_cache=True)
    return _authorization_validator


# Example usage and testing
if __name__ == "__main__":
    # Create user with analyst role
    user = UserContext(
        user_id="user_123",
        username="john.analyst",
        email="john@company.com",
        roles=[Role.ANALYST],
        table_permissions=[
            TablePermission(
                table_name="orders",
                can_query=True,
                can_view=True,
                denied_columns=["customer_ssn", "credit_card"]
            ),
            TablePermission(
                table_name="customers",
                can_query=True,
                can_view=True,
                allowed_columns=["id", "name", "email"]  # Only these columns
            )
        ],
        rls_filters=[
            RLSFilter(
                table_name="orders",
                filter_condition="region = 'US' AND order_date >= '2024-01-01'",
                description="US orders from 2024 onwards"
            )
        ]
    )
    
    # Test permissions
    print(f"Has QUERY_DATA permission: {user.has_permission(Permission.QUERY_DATA)}")
    print(f"Can access orders table: {user.can_access_table('orders')}")
    print(f"Can access payroll table: {user.can_access_table('payroll')}")
    print(f"Can access orders.amount: {user.can_access_column('orders', 'amount')}")
    print(f"Can access orders.customer_ssn: {user.can_access_column('orders', 'customer_ssn')}")
    print(f"Can access customers.id: {user.can_access_column('customers', 'id')}")
    print(f"Can access customers.salary: {user.can_access_column('customers', 'salary')}")
    print(f"RLS filters for orders: {user.get_rls_filters_for_table('orders')}")
    
    # Test validator
    validator = get_authorization_validator()
    allowed, error = validator.validate_table_access(user, "orders")
    print(f"\nValidate orders access: {allowed}, {error}")
    
    allowed, error = validator.validate_column_access(user, "orders", "customer_ssn")
    print(f"Validate orders.customer_ssn access: {allowed}, {error}")
