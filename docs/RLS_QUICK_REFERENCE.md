# RLS Configuration Quick Reference

## 🚀 Quick Start

### 1. Apply Database Migration
```bash
psql -U your_user -d your_database -f migrations/008_add_user_rls_config.sql
```

### 2. Configure via UI
1. Navigate to `http://localhost:3000/rls-config`
2. Select user and connection
3. Assign role (ADMIN, ANALYST, VIEWER)
4. Add RLS filters (table, column, operator, value)

### 3. Example: Bhanu → Region 1, ANBCD → Region 2

**Bhanu Configuration:**
- User: Bhanu
- Role: ANALYST
- Filter: `companies.region = "Region 1"`

**ANBCD Configuration:**
- User: ANBCD
- Role: ANALYST
- Filter: `companies.region = "Region 2"`

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rls/filters` | POST | Create RLS filter |
| `/api/v1/rls/filters/user/{id}/connection/{id}` | GET | Get user filters |
| `/api/v1/rls/filters/{id}` | PUT | Update filter |
| `/api/v1/rls/filters/{id}` | DELETE | Delete filter |
| `/api/v1/rls/roles` | POST | Assign role |
| `/api/v1/rls/roles/user/{id}` | GET | Get user roles |
| `/api/v1/rls/config/user/{id}/connection/{id}` | GET | Get complete config |
| `/api/v1/query/natural-rls` | POST | Execute query with RLS |
| `/api/v1/query/rls-status/connection/{id}` | GET | Check RLS status |

## 🔧 Code Integration

### Basic Integration
```python
from src.user.rls_loader import load_user_context_for_api
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest

# Load user RLS config
user_context = await load_user_context_for_api(
    db=db,
    user_id=current_user.id,
    connection_id=connection_id,
    enable_rls=True
)

# Execute query with RLS
orchestrator = QueryOrchestrator(connection_id=connection_id)
request = QueryRequest(
    natural_language_query=query,
    user_context=user_context,
    enable_rls=True
)
result = await orchestrator.execute_query(request)
```

## 🎯 Common Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `=` | `"Region 1"` | Equals |
| `!=` | `"Region 1"` | Not equals |
| `IN` | `["Region 1", "Region 2"]` | In list |
| `NOT IN` | `["Internal"]` | Not in list |
| `>` | `1000` | Greater than |
| `>=` | `1000` | Greater than or equal |
| `<` | `1000` | Less than |
| `<=` | `1000` | Less than or equal |
| `LIKE` | `"%Sales%"` | Pattern match |
| `NOT LIKE` | `"%Test%"` | Not matching pattern |

## 👥 Roles

| Role | Permissions |
|------|-------------|
| **ADMIN** | Full access, manage users |
| **ANALYST** | Query data, view metrics, view insights |
| **VIEWER** | Query data, view metrics |
| **EXTERNAL** | Query data only (limited) |

## 📋 Filter Value Formats

### String Value
```json
"Region 1"
```

### Number Value
```json
1000
```

### Array (for IN operator)
```json
["Region 1", "Region 2", "Region 3"]
```

### Date Value
```json
"2024-01-01"
```

## 🧪 Testing

### Test Query with RLS
```bash
curl -X POST "http://localhost:8000/api/v1/query/natural-rls" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all companies",
    "connection_id": 1,
    "enable_rls": true
  }'
```

### Check RLS Status
```bash
curl "http://localhost:8000/api/v1/query/rls-status/connection/1" \
  -H "Authorization: Bearer <token>"
```

### Expected Output
```json
{
  "rls_enabled": true,
  "user_id": 1,
  "username": "bhanu",
  "rls_summary": {
    "roles": ["ANALYST"],
    "rls_filters_count": 1,
    "rls_filters": [
      {
        "table": "companies",
        "column": "region",
        "operator": "=",
        "value": "Region 1"
      }
    ]
  }
}
```

## 🎨 UI Components

### Filter Editor
- **Table**: Dropdown (from schema)
- **Column**: Dropdown (from selected table)
- **Operator**: Dropdown (=, !=, IN, etc.)
- **Value**: Text input (JSON format)

### Role Selector
- Dropdown with predefined roles
- Auto-saves on change
- Shows current role

### Filter List
- View all active filters
- Edit/Delete buttons
- Active/Inactive status
- Last updated timestamp

## 💡 Common Scenarios

### Multi-Tenant (Organization-based)
```python
RLSFilter(
    table="companies",
    column="organization_id",
    operator="=",
    value=user.organization_id
)
```

### Regional Access
```python
RLSFilter(
    table="companies",
    column="region",
    operator="IN",
    value=["Region 1", "Region 2"]
)
```

### Department-Based
```python
RLSFilter(
    table="employees",
    column="department",
    operator="=",
    value="Engineering"
)
```

### Time-Based Access
```python
RLSFilter(
    table="transactions",
    column="date",
    operator=">=",
    value="2024-01-01"
)
```

## ⚡ Performance Tips

### 1. Index RLS Columns
```sql
CREATE INDEX idx_companies_region ON companies(region);
CREATE INDEX idx_companies_org_id ON companies(organization_id);
```

### 2. Use Specific Operators
- Prefer `=` over `LIKE`
- Use `IN` for multiple exact matches
- Avoid `NOT LIKE` if possible

### 3. Limit Filter Count
- Combine related filters
- Use table-level permissions when possible
- More filters = slower queries

## 🔒 Security Checklist

- ✅ Always enable RLS for user queries (`enable_rls=True`)
- ✅ Disable RLS only for system/admin queries
- ✅ Validate filter values before saving
- ✅ Review audit logs regularly
- ✅ Use least privilege (start with VIEWER role)
- ✅ Test with multiple users
- ✅ Index RLS columns for performance

## 🐛 Troubleshooting

### No Results Returned
```bash
# Check filter values match data
SELECT DISTINCT region FROM companies;

# Verify filter exists
curl "http://localhost:8000/api/v1/rls/filters/user/1/connection/1" \
  -H "Authorization: Bearer <token>"
```

### Permission Denied
```bash
# Check user role
curl "http://localhost:8000/api/v1/rls/roles/user/1" \
  -H "Authorization: Bearer <token>"
```

### Filters Not Applied
```bash
# Verify enable_rls=true in request
# Check user has active filters (is_active=TRUE)
# Confirm correct connection_id
```

## 📖 Documentation

- **Setup Guide**: [docs/RLS_SETUP_GUIDE.md](./RLS_SETUP_GUIDE.md)
- **Configuration**: [docs/RLS_CONFIGURATION.md](./RLS_CONFIGURATION.md)
- **Security Patterns**: [docs/THOUGHTSPOT_PATTERNS.md](./THOUGHTSPOT_PATTERNS.md)

## 🎯 Quick Commands

```bash
# Apply migration
psql -U postgres -d datatruth -f migrations/008_add_user_rls_config.sql

# Start UI
cd frontend && npm start

# Start API
cd .. && python -m uvicorn src.api.main:app --reload

# Access UI
open http://localhost:3000/rls-config

# Test API
curl http://localhost:8000/docs
```

## 📞 Support

For issues or questions:
1. Check [docs/RLS_SETUP_GUIDE.md](./RLS_SETUP_GUIDE.md) for detailed instructions
2. Review audit logs: `SELECT * FROM rls_configuration_audit ORDER BY performed_at DESC LIMIT 10`
3. Check application logs for RLS-related errors
4. Verify database migration completed successfully
