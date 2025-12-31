# Row-Level Security (RLS) Configuration

## Overview

DataTruth supports enterprise-grade Row-Level Security (RLS) to control data access at the row level based on user context. RLS is **opt-in** by default to maintain backward compatibility with existing deployments.

## Quick Start

### Default Behavior (No RLS)

By default, queries execute with full admin access:

```python
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest

orchestrator = QueryOrchestrator(connection_id=1)
request = QueryRequest(
    natural_language_query="What is the average cost of transactions for companies in the technology industry?"
)
result = await orchestrator.execute_query(request)
```

### Enabling RLS

To enable RLS, provide a `UserContext` and set `enable_rls=True`:

```python
from src.user.authorization import UserContext, Role, RLSFilter
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest

# Define user with RLS filters
user_context = UserContext(
    user_id="user123",
    username="analyst@company.com",
    roles=[Role.ANALYST],
    rls_filters=[
        RLSFilter(
            table="companies",
            column="region",
            operator="=",
            value="EMEA"
        )
    ]
)

# Execute query with RLS
orchestrator = QueryOrchestrator(connection_id=1)
request = QueryRequest(
    natural_language_query="Show me all transactions",
    user_context=user_context,
    enable_rls=True  # Explicitly enable RLS
)
result = await orchestrator.execute_query(request)
```

## Architecture

### 1. User Context

The `UserContext` object defines:
- **User Identity**: user_id, username, email
- **Roles**: ADMIN, ANALYST, VIEWER, EXTERNAL
- **Permissions**: Database, table, column, metric access
- **RLS Filters**: Row-level filters to inject into queries

```python
from src.user.authorization import UserContext, Role, Permission, TablePermission, RLSFilter

user_context = UserContext(
    user_id="user123",
    username="analyst@company.com",
    roles=[Role.ANALYST],
    permissions=[Permission.QUERY_DATA, Permission.VIEW_METRICS],
    table_permissions=[
        TablePermission(
            table="transactions",
            allowed_columns=["id", "amount", "date", "company_id"],
            denied_columns=["credit_card_number"]
        )
    ],
    rls_filters=[
        RLSFilter(table="companies", column="region", operator="=", value="EMEA")
    ]
)
```

### 2. RLS Engine

The `RLSEngine` automatically injects WHERE clauses based on user filters:

**Original Query:**
```sql
SELECT t.amount, c.name
FROM transactions t
JOIN companies c ON t.company_id = c.id
WHERE c.industry = 'technology'
```

**With RLS Filter (region = 'EMEA'):**
```sql
SELECT t.amount, c.name
FROM transactions t
JOIN companies c ON t.company_id = c.id
WHERE c.industry = 'technology'
  AND c.region = 'EMEA'  -- Injected by RLS engine
```

### 3. Authorization Validator

Before query execution, the system validates:
- User has permission to query data
- User can access all referenced tables
- User can access all referenced columns
- User can access all referenced metrics

## Configuration Options

### QueryRequest Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_context` | `Optional[UserContext]` | `None` | User context with permissions and RLS filters. If `None`, uses default admin context |
| `enable_rls` | `bool` | `False` | Whether to apply RLS filters. Must be `True` to inject RLS |
| `validation_level` | `ValidationLevel` | `MODERATE` | SQL validation strictness: STRICT, MODERATE, PERMISSIVE |

### Validation Levels

- **STRICT**: Maximum security, blocks any potentially unsafe operations
- **MODERATE**: Balanced security and usability (recommended)
- **PERMISSIVE**: Minimal restrictions, trust user input (not recommended for production)

## Common Use Cases

### 1. Multi-Tenant SaaS

Ensure users only see their own organization's data:

```python
user_context = UserContext(
    user_id=current_user.id,
    username=current_user.email,
    roles=[Role.ANALYST],
    rls_filters=[
        RLSFilter(
            table="companies",
            column="organization_id",
            operator="=",
            value=current_user.organization_id
        ),
        RLSFilter(
            table="transactions",
            column="organization_id",
            operator="=",
            value=current_user.organization_id
        )
    ]
)
```

### 2. Regional Data Access

Restrict access by geographic region:

```python
user_context = UserContext(
    user_id=user_id,
    username=username,
    roles=[Role.ANALYST],
    rls_filters=[
        RLSFilter(
            table="companies",
            column="region",
            operator="IN",
            value=["EMEA", "APAC"]  # Multiple regions
        )
    ]
)
```

### 3. Department-Based Access

Limit data to specific departments:

```python
user_context = UserContext(
    user_id=user_id,
    username=username,
    roles=[Role.VIEWER],
    rls_filters=[
        RLSFilter(
            table="employees",
            column="department",
            operator="=",
            value="Engineering"
        )
    ]
)
```

## Integration with API

### FastAPI Route Example

```python
from fastapi import Depends, HTTPException
from src.user.authorization import get_user_context
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest

@app.post("/api/v1/query/natural")
async def execute_natural_language_query(
    query: str,
    connection_id: int,
    current_user: User = Depends(get_current_user)
):
    # Build user context from authenticated user
    user_context = UserContext(
        user_id=current_user.id,
        username=current_user.email,
        roles=current_user.roles,
        rls_filters=current_user.get_rls_filters()
    )
    
    # Execute query with RLS
    orchestrator = QueryOrchestrator(connection_id=connection_id)
    request = QueryRequest(
        natural_language_query=query,
        user_context=user_context,
        enable_rls=True  # Enable for authenticated users
    )
    
    try:
        result = await orchestrator.execute_query(request)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
```

## Best Practices

### 1. Always Enable RLS for User-Facing Queries

```python
# ✅ Good: RLS enabled for user queries
request = QueryRequest(
    natural_language_query=query,
    user_context=user_context,
    enable_rls=True
)

# ❌ Bad: RLS disabled for user queries (security risk)
request = QueryRequest(
    natural_language_query=query,
    user_context=user_context,
    enable_rls=False
)
```

### 2. Use Default Context Only for System Queries

```python
# ✅ Good: Default admin context for background jobs
request = QueryRequest(
    natural_language_query="Calculate daily aggregates"
    # No user_context = uses default admin
)

# ❌ Bad: Admin context for user-facing queries
request = QueryRequest(
    natural_language_query=user_input
    # Missing user_context = security risk
)
```

### 3. Cache User Contexts

Authorization checks are cached for performance, but create user context once per request:

```python
# ✅ Good: Create context once
user_context = create_user_context(current_user)
for query in queries:
    result = await orchestrator.execute_query(
        QueryRequest(
            natural_language_query=query,
            user_context=user_context,
            enable_rls=True
        )
    )

# ❌ Bad: Creating context repeatedly
for query in queries:
    user_context = create_user_context(current_user)  # Inefficient
    result = await orchestrator.execute_query(...)
```

### 4. Validate RLS Filters

Always validate that RLS filters are correctly configured:

```python
# ✅ Good: Validate filters before creating context
if not user.organization_id:
    raise ValueError("User must have organization_id for RLS")

user_context = UserContext(
    user_id=user.id,
    username=user.email,
    roles=user.roles,
    rls_filters=[
        RLSFilter(
            table="companies",
            column="organization_id",
            operator="=",
            value=user.organization_id
        )
    ]
)
```

## Testing RLS

### Unit Tests

```python
import pytest
from src.user.authorization import UserContext, Role, RLSFilter
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest

@pytest.mark.asyncio
async def test_rls_filters_applied():
    """Test that RLS filters are correctly injected"""
    user_context = UserContext(
        user_id="test_user",
        username="test@example.com",
        roles=[Role.ANALYST],
        rls_filters=[
            RLSFilter(
                table="companies",
                column="region",
                operator="=",
                value="EMEA"
            )
        ]
    )
    
    orchestrator = QueryOrchestrator(connection_id=1)
    request = QueryRequest(
        natural_language_query="Show all companies",
        user_context=user_context,
        enable_rls=True
    )
    
    result = await orchestrator.execute_query(request)
    
    # Verify RLS was applied
    assert "region = 'EMEA'" in result.sql_query.lower()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_rls_isolates_tenants():
    """Test that users only see their tenant's data"""
    # Create two users from different organizations
    user1_context = create_user_context(org_id="org1")
    user2_context = create_user_context(org_id="org2")
    
    # Execute same query for both users
    orchestrator = QueryOrchestrator(connection_id=1)
    
    result1 = await orchestrator.execute_query(
        QueryRequest(
            natural_language_query="Count all transactions",
            user_context=user1_context,
            enable_rls=True
        )
    )
    
    result2 = await orchestrator.execute_query(
        QueryRequest(
            natural_language_query="Count all transactions",
            user_context=user2_context,
            enable_rls=True
        )
    )
    
    # Verify results are different (isolated by tenant)
    assert result1.data != result2.data
```

## Troubleshooting

### Query Returns No Results

**Symptom**: Query returns empty result set after enabling RLS

**Cause**: RLS filters are too restrictive or incorrect

**Solution**:
1. Verify RLS filters match data in tables:
   ```python
   # Check what data exists
   SELECT DISTINCT region FROM companies;
   
   # Verify filter value exists
   SELECT COUNT(*) FROM companies WHERE region = 'EMEA';
   ```

2. Review RLS filter configuration:
   ```python
   print(user_context.rls_filters)
   # Ensure table/column names and values are correct
   ```

3. Test without RLS to isolate issue:
   ```python
   # Disable RLS temporarily
   request = QueryRequest(
       natural_language_query=query,
       user_context=user_context,
       enable_rls=False  # Disable to test
   )
   ```

### Permission Denied Errors

**Symptom**: `PermissionError` when executing queries

**Cause**: User lacks required permissions

**Solution**:
1. Check user roles:
   ```python
   print(user_context.roles)
   # Ensure user has appropriate role (ANALYST, ADMIN, etc.)
   ```

2. Verify table permissions:
   ```python
   print(user_context.table_permissions)
   # Ensure user can access required tables
   ```

3. Grant appropriate permissions:
   ```python
   user_context = UserContext(
       user_id=user_id,
       username=username,
       roles=[Role.ANALYST],
       permissions=[Permission.QUERY_DATA],  # Add this
       table_permissions=[
           TablePermission(
               table="transactions",
               allowed_columns=["*"]  # Grant column access
           )
       ]
   )
   ```

## Performance Considerations

### 1. Index RLS Columns

Ensure columns used in RLS filters are indexed:

```sql
CREATE INDEX idx_companies_region ON companies(region);
CREATE INDEX idx_companies_organization_id ON companies(organization_id);
CREATE INDEX idx_transactions_organization_id ON transactions(organization_id);
```

### 2. Cache User Contexts

Authorization checks are cached, but avoid creating user contexts repeatedly:

```python
# Cache user context in session/request
@app.middleware("http")
async def add_user_context(request: Request, call_next):
    if request.user:
        request.state.user_context = create_user_context(request.user)
    return await call_next(request)
```

### 3. Monitor Query Performance

Track query execution times with/without RLS:

```python
import time

start = time.time()
result = await orchestrator.execute_query(request)
duration = time.time() - start

logger.info(f"Query executed in {duration:.2f}s (RLS: {request.enable_rls})")
```

## Migration Guide

### Existing Deployments

For existing deployments without RLS:

1. **No Changes Required**: Default behavior is backward compatible
2. **Optional**: Enable RLS gradually by updating API routes
3. **Test**: Verify existing queries work unchanged

### Enabling RLS

To add RLS to existing deployment:

1. Define user context creation logic:
   ```python
   def create_user_context(user: User) -> UserContext:
       return UserContext(
           user_id=user.id,
           username=user.email,
           roles=get_user_roles(user),
           rls_filters=get_user_rls_filters(user)
       )
   ```

2. Update API routes to pass user context:
   ```python
   @app.post("/api/v1/query/natural")
   async def execute_query(
       query: str,
       current_user: User = Depends(get_current_user)
   ):
       user_context = create_user_context(current_user)
       request = QueryRequest(
           natural_language_query=query,
           user_context=user_context,
           enable_rls=True  # Enable RLS
       )
       return await orchestrator.execute_query(request)
   ```

3. Test thoroughly with different user roles and filters

## See Also

- [THOUGHTSPOT_PATTERNS.md](./THOUGHTSPOT_PATTERNS.md) - Enterprise security architecture
- [SECURITY.md](./SECURITY.md) - Overall security practices
- [src/user/authorization.py](../src/user/authorization.py) - Authorization implementation
- [src/user/rls_engine.py](../src/user/rls_engine.py) - RLS engine implementation
