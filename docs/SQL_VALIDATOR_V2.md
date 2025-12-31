# SQL Validator v2 - Production-Grade Implementation

## Overview

The new SQL validator (`validator_v2.py`) replaces regex-based validation with proper AST parsing, providing production-grade security and semantic validation for LLM-generated SQL.

## Critical Issues Fixed

### 1. ❌ Regex-Based Validation → ✅ AST Parsing

**Old Approach:**
```python
# Brittle regex matching
if re.search(rf"\b{keyword}\b", sql_upper):
    errors.append(f"Forbidden keyword detected: {keyword}")
```

**Problems:**
- Easy to bypass with comments: `/* DROP */ SELECT`
- False positives on valid queries
- Can't understand context
- Misses complex constructs

**New Approach:**
```python
# Parse SQL into AST
parsed = sqlparse.parse(sql)
statement = parsed[0]
stmt_type = statement.get_type()  # Returns 'SELECT', 'INSERT', etc.
```

**Benefits:**
- Understands SQL structure
- Context-aware validation
- Handles complex SQL correctly
- No false positives from string matching

---

### 2. ❌ Missing Patterns → ✅ Comprehensive Validation

**Old Code (with `...` placeholders):**
```python
FORBIDDEN_PATTERNS = {
    r";.*?(?:DROP|DELETE)": "multiple statements",
    r"--.*": "SQL comments",
    ...  # Incomplete!
}
```

**New Implementation:**
- ✅ Security validation (SQL injection, dangerous operations)
- ✅ Structure validation (CTEs, subqueries, JOINs, nesting depth)
- ✅ Schema validation (table/column existence)
- ✅ Performance validation (SELECT *, missing WHERE, excessive complexity)
- ✅ Function validation (whitelist approach)
- ✅ LIMIT clause validation

---

### 3. ❌ Can't Handle Complex SQL → ✅ Full SQL Support

**Old Validator Fails On:**

```sql
-- CTEs (Common Table Expressions)
WITH monthly_revenue AS (
  SELECT date_trunc('month', order_date) AS month, SUM(amount) AS revenue
  FROM orders
  WHERE order_date >= '2024-01-01'
  GROUP BY 1
)
SELECT * FROM monthly_revenue LIMIT 100;
-- ❌ Old: Rejects due to "WITH" keyword confusion
```

```sql
-- Nested queries
SELECT customer_id, 
       (SELECT COUNT(*) FROM orders WHERE orders.customer_id = customers.id) as order_count
FROM customers
WHERE country = 'USA'
LIMIT 100;
-- ❌ Old: Can't track subquery context
```

```sql
-- Type casting
SELECT 
  customer_id,
  revenue::numeric(10,2) AS formatted_revenue,
  CAST(order_date AS DATE) AS order_day
FROM orders
LIMIT 100;
-- ❌ Old: Rejects :: as suspicious
```

```sql
-- Quoted identifiers
SELECT "Customer Name", "Order Total"
FROM "Sales Data"
WHERE "Region" = 'West'
LIMIT 100;
-- ❌ Old: Confused by quotes
```

**New Validator Handles All:**
- ✅ CTEs with proper depth tracking
- ✅ Nested subqueries with depth limits
- ✅ Type casting (CAST, ::)
- ✅ Quoted identifiers
- ✅ Complex functions (date_trunc, CASE WHEN, etc.)
- ✅ Window functions
- ✅ Array operations

---

## Architecture

### Validation Levels

```python
class ValidationLevel(str, Enum):
    STRICT = "strict"        # Maximum security, minimal SQL features
    MODERATE = "moderate"    # Balanced (default)
    PERMISSIVE = "permissive"  # Minimal restrictions
```

### Structured Errors

```python
class ValidationError(BaseModel):
    code: str              # Error code (e.g., "FORBIDDEN_OPERATION")
    message: str           # Human-readable message
    severity: str          # "error", "warning", "info"
    location: Optional[str]  # Where in SQL
    context: Optional[Dict]  # Additional details
```

### Validation Pipeline

```
Input SQL
    ↓
1. Parse SQL → AST
    ↓
2. Security Validation
   - Forbidden operations (DROP, DELETE, etc.)
   - SQL injection patterns
   - Dangerous functions (xp_cmdshell, etc.)
   - Multiple statements
    ↓
3. Structure Validation
   - Statement type (must be SELECT)
   - CTEs detection
   - JOIN counting
   - Nesting depth
   - Function whitelisting
    ↓
4. Schema Validation (if semantic_context provided)
   - Table existence
   - Column existence
   - Metric/dimension references
    ↓
5. Performance Validation
   - SELECT * warnings
   - Missing WHERE with JOINs
   - Excessive nesting
    ↓
6. LIMIT Validation
   - LIMIT presence
   - LIMIT value < max
    ↓
Output: SQLValidationResult
```

---

## Usage Examples

### Basic Usage

```python
from src.sql.validator_v2 import ProductionSQLValidator, ValidationLevel

validator = ProductionSQLValidator(
    validation_level=ValidationLevel.MODERATE,
    max_row_limit=10000,
    require_limit=True
)

# Validate SQL
sql = """
SELECT customer_id, SUM(amount) as total_revenue
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY customer_id
LIMIT 100
"""

result = validator.validate(sql)

if result.is_valid:
    print("✅ SQL is valid")
    print(f"Metadata: {result.metadata}")
else:
    print("❌ SQL validation failed:")
    for error in result.errors:
        print(f"  [{error.code}] {error.message}")

# Warnings (non-blocking)
for warning in result.warnings:
    print(f"  ⚠️ [{warning.code}] {warning.message}")
```

### With Semantic Context

```python
semantic_context = {
    "metrics": [
        {"name": "revenue", "table": "orders", "column": "amount"},
        {"name": "order_count", "table": "orders", "column": "id"}
    ],
    "dimensions": [
        {"name": "customer_id", "table": "orders", "column": "customer_id"},
        {"name": "order_date", "table": "orders", "column": "order_date"}
    ]
}

validator = ProductionSQLValidator(
    semantic_context=semantic_context,
    validation_level=ValidationLevel.MODERATE
)

# This will validate table/column references
result = validator.validate(sql)
```

### Strict Mode (Maximum Security)

```python
validator = ProductionSQLValidator(
    validation_level=ValidationLevel.STRICT,
    max_query_depth=3,  # Limit nesting
    max_joins=5,        # Limit JOINs
    require_limit=True
)

# Only whitelisted functions allowed
sql = "SELECT customer_id, CUSTOM_FUNC(amount) FROM orders LIMIT 100"
result = validator.validate(sql)
# ❌ Error: Function not in allowed list: CUSTOM_FUNC
```

---

## Validation Results

### Example: Valid Query

```python
sql = """
WITH monthly_sales AS (
  SELECT 
    date_trunc('month', order_date) AS month,
    SUM(amount) AS revenue
  FROM orders
  WHERE order_date >= '2024-01-01'
  GROUP BY 1
)
SELECT month, revenue
FROM monthly_sales
ORDER BY month DESC
LIMIT 12
"""

result = validator.validate(sql)
```

**Result:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "metadata": {
    "query_length": 245,
    "has_cte": true,
    "has_subquery": false,
    "join_count": 0,
    "query_depth": 1,
    "statement_type": "SELECT"
  }
}
```

### Example: Invalid Query (SQL Injection)

```python
sql = "SELECT * FROM users WHERE username = 'admin' OR '1'='1' LIMIT 100"
result = validator.validate(sql)
```

**Result:**
```json
{
  "is_valid": false,
  "errors": [
    {
      "code": "SQL_INJECTION_RISK",
      "message": "SQL injection risk: SQL injection pattern: OR '1'='1'",
      "severity": "error",
      "location": "'\s*OR\s*'1'\s*=\s*'1"
    }
  ],
  "warnings": [
    {
      "code": "SELECT_STAR",
      "message": "SELECT * may impact performance, consider explicit columns",
      "severity": "warning"
    }
  ],
  "metadata": {...}
}
```

### Example: Invalid Query (Forbidden Operation)

```python
sql = "DROP TABLE users; SELECT * FROM customers LIMIT 100"
result = validator.validate(sql)
```

**Result:**
```json
{
  "is_valid": false,
  "errors": [
    {
      "code": "FORBIDDEN_OPERATION",
      "message": "Forbidden operation detected: DROP",
      "severity": "error",
      "context": {"operation": "DROP"}
    },
    {
      "code": "MULTIPLE_STATEMENTS",
      "message": "Multiple SQL statements not allowed",
      "severity": "error",
      "context": {"statement_count": 2}
    }
  ]
}
```

### Example: Warnings Only

```python
sql = """
SELECT *
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id
JOIN categories cat ON p.category_id = cat.id
LIMIT 1000
"""

result = validator.validate(sql)
```

**Result:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [
    {
      "code": "SELECT_STAR",
      "message": "SELECT * may impact performance, consider explicit columns",
      "severity": "warning"
    },
    {
      "code": "MISSING_WHERE",
      "message": "Query with JOINs but no WHERE clause may be inefficient",
      "severity": "warning",
      "context": {"join_count": 3}
    }
  ],
  "metadata": {
    "join_count": 3,
    "query_depth": 1
  }
}
```

---

## Security Features

### 1. SQL Injection Protection

**Detected Patterns:**
- `' OR '1'='1'` - Classic injection
- `' OR 1=1 --` - Comment-based injection
- `UNION SELECT` - Union-based injection
- `; DROP TABLE` - Multiple statement injection
- `/* */ DROP` - Comment obfuscation

**Example:**
```python
# All of these are blocked:
"SELECT * FROM users WHERE id = 1; DROP TABLE users"
"SELECT * FROM users WHERE name = '' OR '1'='1'"
"SELECT * FROM users UNION SELECT password FROM admin"
```

### 2. Dangerous Function Blocking

**Blocked Functions:**
- System access: `xp_cmdshell`, `system`, `shell`
- File operations: `load_file`, `into outfile`, `pg_read_file`
- Code execution: `exec`, `sp_executesql`, `dbms_java`

**Allowed Functions:**
- Aggregates: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`
- String: `UPPER`, `LOWER`, `CONCAT`, `SUBSTRING`
- Date: `DATE_TRUNC`, `EXTRACT`, `NOW`
- Math: `ROUND`, `FLOOR`, `CEIL`, `ABS`
- Conditional: `CASE`, `COALESCE`, `NULLIF`

### 3. Operation Restrictions

**Forbidden Operations:**
- DDL: `DROP`, `CREATE`, `ALTER`
- DML: `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`
- DCL: `GRANT`, `REVOKE`

**Only Allowed:**
- `SELECT` statements

---

## Performance Features

### 1. Complexity Limits

```python
validator = ProductionSQLValidator(
    max_query_depth=5,    # Maximum subquery nesting
    max_joins=10,         # Maximum JOIN count
    max_row_limit=10000   # Maximum LIMIT value
)
```

**Prevents:**
- Excessive subquery nesting (cartesian explosion)
- Too many JOINs (performance degradation)
- Unbounded result sets (memory issues)

### 2. Performance Warnings

**Detected Issues:**
- `SELECT *` without explicit columns
- JOINs without WHERE clause
- Deep nesting (> 3 levels)
- Missing indexes (if schema metadata available)

---

## Schema Validation

### Integration with Semantic Layer

```python
# Load semantic context
semantic_context = {
    "metrics": [
        {
            "name": "revenue",
            "table": "orders",
            "column": "amount",
            "aggregation": "SUM"
        }
    ],
    "dimensions": [
        {
            "name": "customer_id",
            "table": "orders",
            "column": "customer_id"
        }
    ]
}

validator = ProductionSQLValidator(semantic_context=semantic_context)
```

**Validates:**
- Table references exist in semantic layer
- Column references exist in tables
- Metric names match semantic definitions
- Dimension names match semantic definitions

**Example:**
```python
# Valid - uses known tables/columns
sql = "SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id LIMIT 100"
# ✅ Pass

# Invalid - unknown table
sql = "SELECT * FROM unknown_table LIMIT 100"
# ⚠️ Warning: Table not found in semantic layer: unknown_table

# Invalid - unknown column
sql = "SELECT fake_column FROM orders LIMIT 100"
# ⚠️ Warning: Column fake_column not found in table orders
```

---

## Migration Guide

### Phase 1: Side-by-Side Testing

```python
from src.sql.validator import SQLValidator  # Old
from src.sql.validator_v2 import ProductionSQLValidator  # New

# Run both validators
old_validator = SQLValidator()
new_validator = ProductionSQLValidator()

is_valid_old, errors_old = old_validator.validate(sql)
result_new = new_validator.validate(sql)

# Compare results
print(f"Old: {is_valid_old}, New: {result_new.is_valid}")
```

### Phase 2: Gradual Rollout

```python
import os

if os.getenv("USE_V2_VALIDATOR", "false") == "true":
    from src.sql.validator_v2 import ProductionSQLValidator as SQLValidator
else:
    from src.sql.validator import SQLValidator
```

### Phase 3: Full Replacement

```python
# Update imports everywhere
from src.sql.validator_v2 import ProductionSQLValidator

# Update orchestrator_v2.py
validator = ProductionSQLValidator(
    semantic_context=semantic_context,
    validation_level=ValidationLevel.MODERATE,
    max_row_limit=self.max_row_limit
)
```

---

## Testing Recommendations

### 1. Security Tests

```python
def test_sql_injection_blocked():
    validator = ProductionSQLValidator()
    
    injection_attempts = [
        "SELECT * FROM users WHERE id = 1; DROP TABLE users",
        "SELECT * FROM users WHERE name = '' OR '1'='1'",
        "SELECT * FROM users UNION SELECT password FROM admin",
    ]
    
    for sql in injection_attempts:
        result = validator.validate(sql)
        assert not result.is_valid
        assert any(e.code == "SQL_INJECTION_RISK" for e in result.errors)
```

### 2. Complex SQL Tests

```python
def test_cte_support():
    validator = ProductionSQLValidator(require_limit=True)
    
    sql = """
    WITH monthly_revenue AS (
      SELECT date_trunc('month', order_date) AS month, SUM(amount) AS revenue
      FROM orders
      WHERE order_date >= '2024-01-01'
      GROUP BY 1
    )
    SELECT month, revenue FROM monthly_revenue ORDER BY month DESC LIMIT 12
    """
    
    result = validator.validate(sql)
    assert result.is_valid
    assert result.metadata['has_cte'] == True
    assert result.metadata['query_depth'] == 1
```

### 3. Schema Validation Tests

```python
def test_schema_validation():
    semantic_context = {
        "metrics": [{"name": "revenue", "table": "orders", "column": "amount"}],
        "dimensions": [{"name": "customer_id", "table": "orders", "column": "customer_id"}]
    }
    
    validator = ProductionSQLValidator(semantic_context=semantic_context)
    
    # Valid query
    sql = "SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id LIMIT 100"
    result = validator.validate(sql)
    assert result.is_valid
    
    # Invalid table
    sql = "SELECT * FROM fake_table LIMIT 100"
    result = validator.validate(sql)
    assert len(result.warnings) > 0
    assert any(w.code == "UNKNOWN_TABLE" for w in result.warnings)
```

---

## Comparison: Old vs New

| Feature | Old Validator | New Validator |
|---------|--------------|---------------|
| **Parsing Method** | ❌ Regex | ✅ AST (sqlparse) |
| **CTEs** | ❌ Not supported | ✅ Full support |
| **Nested Queries** | ❌ Basic check | ✅ Depth tracking |
| **Type Casting** | ❌ False positives | ✅ Correct handling |
| **Quoted Identifiers** | ❌ Fails | ✅ Handles correctly |
| **Function Validation** | ❌ Pattern matching | ✅ Whitelist with AST |
| **SQL Injection** | ⚠️ Basic patterns | ✅ Comprehensive |
| **Schema Validation** | ❌ None | ✅ Full semantic layer |
| **Error Types** | ❌ Strings | ✅ Structured (code, message, context) |
| **Performance Warnings** | ❌ None | ✅ SELECT *, JOINs, etc. |
| **Metadata** | ❌ None | ✅ Depth, JOINs, CTEs, etc. |
| **False Positives** | ❌ High | ✅ Minimal |
| **Extensibility** | ❌ Hardcoded | ✅ Configurable levels |

---

## Future Enhancements

### 1. Cost Estimation
```python
# Estimate query cost before execution
metadata["estimated_cost"] = validator.estimate_cost(sql, statistics)
```

### 2. Query Optimization Suggestions
```python
# Suggest optimizations
result.suggestions = [
    "Add index on orders.customer_id",
    "Consider partitioning on order_date"
]
```

### 3. Machine Learning Integration
```python
# Learn from query patterns
validator.learn_from_execution(sql, execution_time, row_count)
```

### 4. Custom Rules
```python
# Add custom validation rules
validator.add_rule(CustomRule(
    name="no_cross_joins",
    check=lambda sql: "CROSS JOIN" not in sql.upper(),
    error_code="FORBIDDEN_CROSS_JOIN"
))
```

---

## Conclusion

The new SQL validator provides production-grade validation with:

✅ **Proper AST parsing** - No more regex hacks
✅ **Complete SQL support** - CTEs, nested queries, casts, etc.
✅ **Security hardening** - SQL injection, dangerous operations
✅ **Semantic validation** - Schema-aware checking
✅ **Performance insights** - Complexity warnings
✅ **Structured errors** - Typed errors with context
✅ **Extensibility** - Configurable validation levels

This addresses all the critical issues in the original validator and provides a solid foundation for LLM-generated SQL validation.
