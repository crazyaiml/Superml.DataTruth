# QueryOrchestrator Improvements

## Overview

This document describes the critical improvements made to the QueryOrchestrator based on architectural review feedback. The improved version is available in `src/integration/orchestrator_v2.py`.

## Key Issues Addressed

### 1. Real Result Caching ✅

**Problem:** Original implementation always returned `cached=False`, even when results came from cache.

**Solution:**
```python
async def _execute_query(self, sql: str, enable_caching: bool) -> Tuple[List[Dict[str, Any]], bool]:
    """Execute query with REAL result caching."""
    results = await self.query_executor.execute(sql)
    
    # Check actual cache status from executor
    cached = False
    if hasattr(self.query_executor, 'last_query_was_cached'):
        cached = self.query_executor.last_query_was_cached()
    
    return results, cached  # Return real cache status
```

**Benefits:**
- Accurate cache-hit metrics in performance tracking
- Users can see when queries are served from cache
- Better debugging and optimization insights

---

### 2. Multi-Level Validation ✅

**Problem:** Validation only happened on final SQL string, too late to catch plan-level errors.

**Solution:** Added two validation layers:

#### Layer 1: Plan-Level Validation
Validates query plan BEFORE SQL generation:

```python
def _validate_plan(self, query_plan: QueryPlan, semantic_context: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate query plan before SQL generation."""
    errors = []
    
    # Check metrics exist
    available_metrics = {m["name"] for m in semantic_context.get("metrics", [])}
    for metric in query_plan.metrics:
        if metric.name not in available_metrics:
            errors.append(f"Unknown metric: {metric.name}")
    
    # Check dimensions exist
    available_dimensions = {d["name"] for d in semantic_context.get("dimensions", [])}
    for dimension in query_plan.dimensions:
        if dimension.name not in available_dimensions:
            errors.append(f"Unknown dimension: {dimension.name}")
    
    # Validate filters reference valid fields
    # Validate time ranges
    # etc.
    
    return len(errors) == 0, errors
```

#### Layer 2: SQL AST Validation
Validates SQL structure using AST parsing:

```python
def _validate_sql_ast(self, sql: str, semantic_context: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate SQL using AST parsing."""
    errors = []
    
    # Parse SQL
    parsed = sqlparse.parse(sql)
    statement = parsed[0]
    
    # Check statement type (only SELECT allowed)
    stmt_type = statement.get_type()
    if stmt_type != 'SELECT':
        errors.append(f"Only SELECT statements allowed, got {stmt_type}")
    
    # Check for dangerous keywords
    dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE']
    for keyword in dangerous_keywords:
        if keyword in sql.upper():
            errors.append(f"Dangerous keyword detected: {keyword}")
    
    # Check for DELETE/UPDATE without WHERE
    # Verify column names
    # etc.
    
    return len(errors) == 0, errors
```

**Benefits:**
- Catch errors earlier in the pipeline
- Prevent invalid SQL generation
- Security: Block dangerous operations
- Better error messages with context

---

### 3. Typed Errors with Debug Info ✅

**Problem:** Generic `Exception` handling made debugging difficult. No error types or structured debug info.

**Solution:** Introduced typed errors with debug payloads:

```python
class ErrorType(str, Enum):
    """Error types for typed error handling."""
    VALIDATION_ERROR = "validation_error"
    PLAN_ERROR = "plan_error"
    SQL_GENERATION_ERROR = "sql_generation_error"
    EXECUTION_ERROR = "execution_error"
    LLM_ERROR = "llm_error"
    ANALYTICS_ERROR = "analytics_error"
    UNKNOWN_ERROR = "unknown_error"


class QueryError(BaseModel):
    """Structured error information."""
    type: ErrorType
    message: str
    stage: str  # Which pipeline stage failed
    debug_info: Optional[Dict[str, Any]] = None  # Debug payload


def _create_error(self, error_type: ErrorType, stage: str, message: str, 
                  debug_info: Optional[Dict[str, Any]] = None) -> ValueError:
    """Create a typed error with metadata."""
    error = ValueError(message)
    error.type = error_type
    error.stage = stage
    error.debug_info = debug_info
    return error
```

**Example Error Response:**
```json
{
  "success": false,
  "error": {
    "type": "plan_error",
    "message": "Invalid query plan: Unknown metric: invalid_metric",
    "stage": "plan_validation",
    "debug_info": {
      "plan": {"metrics": ["invalid_metric"], "dimensions": []},
      "errors": ["Unknown metric: invalid_metric"]
    }
  }
}
```

**Benefits:**
- Clients can handle different error types appropriately
- Debug info provides context for troubleshooting
- Structured logging and monitoring
- Better error recovery strategies

---

### 4. Analytics on Full Result Set ✅

**Problem:** Analytics ran on paginated results, distorting statistics.

**Solution:** Run analytics BEFORE pagination:

```python
async def execute_query(self, request: QueryRequest) -> QueryResponse:
    """Execute query with proper analytics pipeline."""
    
    # Stage 6: Execute query (FULL result set - no pagination yet)
    full_results, result_cached = await self._execute_query(sql, request.enable_caching)
    
    # Stage 7: Run analytics on FULL result set (before pagination)
    analytics = None
    if request.enable_analytics and full_results:
        analytics = self._calculate_analytics(full_results, query_plan)
        # Analytics now computed on ALL rows
    
    # Stage 8: Apply pagination AFTER analytics
    if request.pagination:
        results, pagination_metadata = paginate_results(
            full_results,
            len(full_results),
            request.pagination
        )
    else:
        results = full_results
```

**Metadata in Analytics:**
```json
{
  "revenue": {
    "statistics": {
      "count": 10000,
      "mean": 54321.45,
      "median": 45000.00,
      "std_dev": 12345.67
    }
  },
  "_metadata": {
    "total_rows": 10000,
    "numeric_columns_analyzed": 5,
    "computed_on_full_dataset": true
  }
}
```

**Benefits:**
- Accurate statistics (mean, median, std_dev)
- Correct anomaly detection
- Trustworthy insights for decision-making
- Transparent metadata about computation

---

## Pipeline Flow

### Original Flow (❌ Issues)
```
1. Load context
2. Extract intent (cached=false always)
3. Generate plan (no validation)
4. Generate SQL
5. Validate SQL string only
6. Execute + paginate together
7. Analytics on paginated results ❌
8. Return (cached=false always)
```

### Improved Flow (✅ Fixed)
```
1. Load context
2. Extract intent (with REAL caching) ✅
3. Validate plan ✅
4. Generate SQL
5. Validate SQL string ✅
6. Validate SQL AST ✅
7. Execute (full results)
8. Analytics on full results ✅
9. Apply pagination
10. Return (with real cache status) ✅
```

---

## Error Handling Comparison

### Before
```python
except Exception as e:
    print(f"Query execution failed: {str(e)}")
    return QueryResponse(
        ...
        explanation=f"Failed to execute query: {str(e)}",
        cached=False
    )
```

**Issues:**
- No error type
- No stage information
- No debug payload
- Generic error message

### After
```python
except ValueError as e:
    # Typed errors with debug info
    if hasattr(e, 'type'):
        error_data = QueryError(
            type=e.type,
            message=str(e),
            stage=e.stage,
            debug_info=e.debug_info
        )
    
    return QueryResponse(
        success=False,
        error=error_data,
        ...
    )
```

**Improvements:**
- Typed errors (VALIDATION_ERROR, EXECUTION_ERROR, etc.)
- Stage tracking (plan_validation, sql_generation, etc.)
- Debug payloads (SQL, plan, errors)
- Structured error response

---

## Performance Metrics

### Before
```json
{
  "performance": {
    "total_time_ms": 1234,
    "stage_timings_ms": {...}
  },
  "cached": false  // Always false ❌
}
```

### After
```json
{
  "performance": {
    "total_time_ms": 1234,
    "stage_timings_ms": {
      "semantic_context": 10,
      "query_planning": 50,
      "plan_validation": 5,      // ✅ New
      "sql_generation": 100,
      "sql_validation": 15,       // ✅ Improved
      "query_execution": 950,
      "analytics": 80,
      "pagination": 4
    },
    "plan_cached": true,         // ✅ Real status
    "result_cached": false       // ✅ Real status
  },
  "cached": false
}
```

---

## Migration Guide

### Option 1: Drop-in Replacement

```python
# Old
from src.integration.orchestrator import get_orchestrator
orchestrator = get_orchestrator()

# New
from src.integration.orchestrator_v2 import get_improved_orchestrator
orchestrator = get_improved_orchestrator()

# API remains compatible
response = await orchestrator.execute_query(request)
```

### Option 2: Gradual Migration

1. Import both versions
2. Run queries through both
3. Compare results in parallel
4. Switch to v2 when confident
5. Remove v1

### Option 3: Feature Flag

```python
if os.getenv("USE_IMPROVED_ORCHESTRATOR", "false") == "true":
    from src.integration.orchestrator_v2 import get_improved_orchestrator as get_orchestrator
else:
    from src.integration.orchestrator import get_orchestrator
```

---

## API Changes

### QueryRequest

Added field:
```python
enable_debug: bool = False  # Include debug info in errors
```

### QueryResponse

Added fields:
```python
success: bool  # Explicit success flag
error: Optional[QueryError] = None  # Structured error info
```

### QueryResponse.performance

Added fields:
```python
{
  "plan_cached": bool,   # Was plan from cache?
  "result_cached": bool  # Was result from cache?
}
```

### QueryResponse.analytics

Added metadata:
```python
{
  "_metadata": {
    "total_rows": int,
    "numeric_columns_analyzed": int,
    "computed_on_full_dataset": true
  }
}
```

---

## Testing Recommendations

### 1. Cache Hit Testing
```python
# First query - should be cache miss
response1 = await orchestrator.execute_query(request)
assert response1.cached == False
assert response1.performance["plan_cached"] == False

# Second query - should be cache hit
response2 = await orchestrator.execute_query(request)
assert response2.cached == True
assert response2.performance["plan_cached"] == True
```

### 2. Validation Testing
```python
# Test plan validation
request = QueryRequest(question="Show me invalid_metric by invalid_dimension")
response = await orchestrator.execute_query(request)
assert response.success == False
assert response.error.type == ErrorType.PLAN_ERROR
assert "Unknown metric" in response.error.message

# Test SQL AST validation
# Mock SQL generator to return dangerous SQL
response = await orchestrator.execute_query(request)
assert response.error.type == ErrorType.VALIDATION_ERROR
assert "Dangerous keyword" in response.error.message
```

### 3. Analytics Testing
```python
# Test analytics on full dataset
request = QueryRequest(
    question="Show me revenue",
    pagination=PaginationParams(page=1, page_size=10)
)
response = await orchestrator.execute_query(request)

# Results are paginated (10 rows)
assert len(response.results) == 10

# But analytics computed on all rows
assert response.analytics["_metadata"]["total_rows"] > 10
assert response.analytics["_metadata"]["computed_on_full_dataset"] == True
```

### 4. Error Type Testing
```python
# Test each error type
error_scenarios = [
    ("invalid metric", ErrorType.PLAN_ERROR),
    ("SQL injection", ErrorType.VALIDATION_ERROR),
    ("database down", ErrorType.EXECUTION_ERROR),
    ("OpenAI timeout", ErrorType.LLM_ERROR),
]

for scenario, expected_type in error_scenarios:
    response = await orchestrator.execute_query(request)
    assert response.error.type == expected_type
```

---

## Future Enhancements

### 1. Query Plan Optimization
- Detect redundant filters
- Suggest index usage
- Rewrite inefficient plans

### 2. Smart Caching Strategies
- Partial result caching
- Invalidation on data updates
- Cache warming for common queries

### 3. Advanced AST Validation
- Column existence checking
- Join condition validation
- Index usage analysis

### 4. Analytics Enhancements
- Time-series analysis
- Trend detection
- Automatic insights generation

### 5. Distributed Execution
- Parallel query execution
- Result streaming
- Resource pooling

---

## Conclusion

The improved QueryOrchestrator addresses all four critical gaps:

1. ✅ **Real Caching**: Accurate cache-hit tracking with metadata
2. ✅ **Multi-Level Validation**: Plan-level + SQL AST validation
3. ✅ **Typed Errors**: Structured errors with debug payloads
4. ✅ **Correct Analytics**: Computed on full result sets

These improvements provide a production-ready orchestration layer with:
- Better debugging capabilities
- Improved security
- Accurate analytics
- Transparent performance metrics
- Structured error handling

The implementation maintains API compatibility while adding opt-in features like debug mode.
