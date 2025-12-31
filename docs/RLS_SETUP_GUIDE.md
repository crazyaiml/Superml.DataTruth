# RLS Configuration Setup Guide

## Overview

This guide walks you through setting up Row-Level Security (RLS) for DataTruth, allowing you to configure fine-grained access control where different users see different data based on their assigned filters.

## Use Case Example

**Scenario**: You want Bhanu (Analyst) to see only Region 1 data, while ANBCD (Analyst) sees only Region 2 data.

**Solution**: Configure RLS filters at the user + connection level.

## Quick Setup (5 minutes)

### Step 1: Run Database Migration

First, apply the RLS configuration schema to your database:

```bash
# Run the migration
psql -U your_user -d your_database -f migrations/008_add_user_rls_config.sql
```

This creates the following tables:
- `user_rls_filters` - Store RLS filters per user/connection
- `user_connection_roles` - Map users to roles per connection
- `user_table_permissions` - Store table/column permissions
- `rls_configuration_audit` - Audit log for configuration changes

### Step 2: Access RLS Configuration UI

Navigate to the RLS Configuration page in DataTruth:

```
http://localhost:3000/rls-config
```

### Step 3: Configure User - Bhanu

1. **Select User**: Choose "Bhanu" from the user dropdown
2. **Select Connection**: Choose your database connection (e.g., "Production DB")
3. **Assign Role**: Select "ANALYST" from the role dropdown
4. **Add RLS Filter**:
   - Click "Add Filter"
   - Table: `companies`
   - Column: `region`
   - Operator: `=`
   - Value: `"Region 1"` (use JSON format with quotes)
   - Click "Save Filter"

### Step 4: Configure User - ANBCD

1. **Select User**: Choose "ANBCD" from the user dropdown
2. **Select Connection**: Choose the same database connection
3. **Assign Role**: Select "ANALYST"
4. **Add RLS Filter**:
   - Click "Add Filter"
   - Table: `companies`
   - Column: `region`
   - Operator: `=`
   - Value: `"Region 2"` (use JSON format with quotes)
   - Click "Save Filter"

### Step 5: Test RLS

**Option A: Use the RLS Query Endpoint**

```bash
# Test as Bhanu (should see Region 1 only)
curl -X POST "http://localhost:8000/api/v1/query/natural-rls" \
  -H "Authorization: Bearer <bhanu_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all companies",
    "connection_id": 1,
    "enable_rls": true
  }'

# Test as ANBCD (should see Region 2 only)
curl -X POST "http://localhost:8000/api/v1/query/natural-rls" \
  -H "Authorization: Bearer <anbcd_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all companies",
    "connection_id": 1,
    "enable_rls": true
  }'
```

**Option B: Check RLS Status**

```bash
# Check Bhanu's RLS configuration
curl "http://localhost:8000/api/v1/query/rls-status/connection/1" \
  -H "Authorization: Bearer <bhanu_token>"
```

Expected output:
```json
{
  "rls_enabled": true,
  "user_id": 1,
  "username": "bhanu",
  "connection_id": 1,
  "rls_summary": {
    "user_id": "1",
    "username": "bhanu",
    "roles": ["ANALYST"],
    "is_admin": false,
    "rls_filters_count": 1,
    "rls_filters": [
      {
        "table": "companies",
        "column": "region",
        "operator": "=",
        "value": "Region 1"
      }
    ]
  },
  "message": "RLS active with 1 filters"
}
```

## Advanced Configuration

### Multiple Filters

You can add multiple RLS filters for a user. All filters are combined with AND logic:

**Example**: Restrict by region AND department
```
Filter 1: companies.region = "Region 1"
Filter 2: companies.department = "Sales"
Result: User sees only Region 1 Sales companies
```

### IN Operator for Multiple Values

Use the IN operator to allow access to multiple values:

**Example**: Access to multiple regions
```
Table: companies
Column: region
Operator: IN
Value: ["Region 1", "Region 2"]
```

### Table-Level Permissions

Configure which tables users can access:

```bash
# Via API
curl -X POST "http://localhost:8000/api/v1/rls/table-permissions" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "connection_id": 1,
    "table_name": "transactions",
    "can_read": true,
    "can_write": false,
    "can_delete": false,
    "allowed_columns": ["id", "amount", "date"],
    "denied_columns": ["credit_card_number"]
  }'
```

### Role-Based Configuration

Different roles have different default permissions:

| Role | Permissions |
|------|-------------|
| **ADMIN** | Query data, view metrics, view insights, manage users |
| **ANALYST** | Query data, view metrics, view insights |
| **VIEWER** | Query data, view metrics |
| **EXTERNAL** | Query data only (limited) |

## Integration with Existing Code

### Option 1: Use the Example Endpoint

The example endpoint is already integrated and ready to use:

```python
# POST /api/v1/query/natural-rls
# Automatically loads RLS config from database
```

### Option 2: Add to Your Existing Endpoint

Add RLS to your existing query endpoint:

```python
from src.user.rls_loader import load_user_context_for_api
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest
from src.database.connection import get_db

@app.post("/api/v1/query/my-endpoint")
async def my_query_endpoint(
    query: str,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Load user RLS configuration
    user_context = await load_user_context_for_api(
        db=db,
        user_id=current_user.id,
        connection_id=connection_id,
        enable_rls=True  # Set to False to disable RLS
    )
    
    # Create orchestrator
    orchestrator = QueryOrchestrator(connection_id=connection_id)
    
    # Execute query with RLS
    request = QueryRequest(
        natural_language_query=query,
        user_context=user_context,
        enable_rls=True
    )
    
    result = await orchestrator.execute_query(request)
    return result
```

## API Reference

### RLS Filter Management

**Create RLS Filter**
```
POST /api/v1/rls/filters
```

**Get User Filters**
```
GET /api/v1/rls/filters/user/{user_id}/connection/{connection_id}
```

**Update Filter**
```
PUT /api/v1/rls/filters/{filter_id}
```

**Delete Filter**
```
DELETE /api/v1/rls/filters/{filter_id}
```

### Role Management

**Assign User Role**
```
POST /api/v1/rls/roles
```

**Get User Roles**
```
GET /api/v1/rls/roles/user/{user_id}
```

### Configuration

**Get Complete RLS Config**
```
GET /api/v1/rls/config/user/{user_id}/connection/{connection_id}
```

### Query Execution

**Execute Query with RLS**
```
POST /api/v1/query/natural-rls
```

**Check RLS Status**
```
GET /api/v1/query/rls-status/connection/{connection_id}
```

## Common Scenarios

### Scenario 1: Multi-Tenant SaaS

Each organization sees only their data:

```python
# Filter by organization_id
user_context = UserContext(
    user_id=user.id,
    username=user.email,
    roles=[Role.ANALYST],
    rls_filters=[
        RLSFilter(
            table="companies",
            column="organization_id",
            operator="=",
            value=user.organization_id
        ),
        RLSFilter(
            table="transactions",
            column="organization_id",
            operator="=",
            value=user.organization_id
        )
    ]
)
```

### Scenario 2: Regional Sales Teams

Sales reps see only their assigned regions:

```python
# Filter by region
user_context = UserContext(
    user_id=user.id,
    username=user.email,
    roles=[Role.ANALYST],
    rls_filters=[
        RLSFilter(
            table="companies",
            column="region",
            operator="IN",
            value=user.assigned_regions  # ["Region 1", "Region 2"]
        )
    ]
)
```

### Scenario 3: Department-Based Access

Users see only their department's data:

```python
# Filter by department
user_context = UserContext(
    user_id=user.id,
    username=user.email,
    roles=[Role.VIEWER],
    rls_filters=[
        RLSFilter(
            table="employees",
            column="department",
            operator="=",
            value=user.department
        ),
        RLSFilter(
            table="projects",
            column="department",
            operator="=",
            value=user.department
        )
    ]
)
```

### Scenario 4: Time-Based Access

Restrict access to recent data only:

```python
# Filter by date range
user_context = UserContext(
    user_id=user.id,
    username=user.email,
    roles=[Role.EXTERNAL],
    rls_filters=[
        RLSFilter(
            table="transactions",
            column="date",
            operator=">=",
            value="2024-01-01"
        )
    ]
)
```

## Troubleshooting

### Issue: Filters not applied

**Check**:
1. Is `enable_rls=True` in the QueryRequest?
2. Does the user have RLS filters configured?
3. Are the filters active (`is_active=TRUE`)?

**Debug**:
```python
# Check user's RLS configuration
curl "http://localhost:8000/api/v1/rls/config/user/1/connection/1" \
  -H "Authorization: Bearer <token>"
```

### Issue: Query returns no results

**Possible causes**:
1. RLS filter value doesn't match any data
2. Multiple filters are too restrictive
3. Table/column names in filter don't match actual schema

**Solution**:
```sql
-- Check what values exist
SELECT DISTINCT region FROM companies;

-- Verify filter matches data
SELECT COUNT(*) FROM companies WHERE region = 'Region 1';
```

### Issue: Permission denied error

**Check**:
1. User has appropriate role assigned
2. User has permission to access the table
3. User has permission to access required columns

**Debug**:
```python
# Check user's permissions
rls_summary = get_rls_summary(user_context)
print(rls_summary)
```

## Performance Optimization

### Index RLS Columns

Create indexes on columns used in RLS filters:

```sql
-- Index for region-based RLS
CREATE INDEX idx_companies_region ON companies(region);
CREATE INDEX idx_transactions_region ON transactions(company_id, region);

-- Index for organization-based RLS
CREATE INDEX idx_companies_org_id ON companies(organization_id);
CREATE INDEX idx_transactions_org_id ON transactions(organization_id);
```

### Cache User Contexts

Avoid loading user context on every request:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_user_context(user_id: int, connection_id: int):
    return load_user_rls_context(db, user_id, connection_id)
```

### Monitor Performance

Track query execution times:

```python
import time

start = time.time()
result = await orchestrator.execute_query(request)
duration = time.time() - start

logger.info(f"Query with RLS: {duration:.2f}s, filters={len(user_context.rls_filters)}")
```

## Security Best Practices

1. **Always enable RLS for user-facing queries**
   - Set `enable_rls=True` by default
   - Only disable for system/admin queries

2. **Validate filter values**
   - Sanitize user input before creating filters
   - Use parameterized queries (handled automatically)

3. **Audit configuration changes**
   - All RLS changes are logged in `rls_configuration_audit`
   - Review audit logs regularly

4. **Test thoroughly**
   - Verify each user sees correct data
   - Test edge cases (no filters, multiple filters, etc.)

5. **Use least privilege**
   - Assign minimal required role
   - Start with VIEWER, upgrade as needed

## Next Steps

1. ✅ Database migration applied
2. ✅ RLS filters configured
3. ✅ Users assigned roles
4. ✅ Queries tested with RLS

**Optional Enhancements**:
- Add dynamic RLS rules based on user attributes
- Implement time-based access (expire filters)
- Add bulk filter management
- Create RLS templates for common scenarios
- Set up monitoring/alerting for RLS violations

## See Also

- [RLS_CONFIGURATION.md](./RLS_CONFIGURATION.md) - Detailed RLS documentation
- [SECURITY.md](./SECURITY.md) - Overall security practices
- [THOUGHTSPOT_PATTERNS.md](./THOUGHTSPOT_PATTERNS.md) - Enterprise patterns
