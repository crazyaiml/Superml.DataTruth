"""
Query Executor

Executes SQL queries with error handling, retries, and performance monitoring.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from src.database.cache import QueryCache, get_query_cache
from src.database.connection import ConnectionPool, get_connection_pool
from src.planner.query_plan import QueryPlan
from src.sql import build_sql, validate_sql

logger = logging.getLogger(__name__)


class QueryExecutionError(Exception):
    """Raised when query execution fails."""

    pass


class QueryResult:
    """Query execution result with metadata."""

    def __init__(
        self,
        rows: List[Dict[str, Any]],
        row_count: int,
        execution_time_ms: float,
        from_cache: bool = False,
        sql: Optional[str] = None,
    ) -> None:
        """
        Initialize query result.

        Args:
            rows: Result rows as list of dicts
            row_count: Number of rows returned
            execution_time_ms: Query execution time in milliseconds
            from_cache: Whether result was retrieved from cache
            sql: Generated SQL query
        """
        self.rows = rows
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.from_cache = from_cache
        self.sql = sql

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "from_cache": self.from_cache,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"QueryResult(row_count={self.row_count}, "
            f"execution_time_ms={self.execution_time_ms:.2f}, "
            f"from_cache={self.from_cache})"
        )


class QueryExecutor:
    """Executes SQL queries with caching and monitoring."""

    def __init__(
        self,
        connection_pool: Optional[ConnectionPool] = None,
        query_cache: Optional[QueryCache] = None,
        max_retries: int = 3,
        retry_delay_ms: int = 100,
    ) -> None:
        """
        Initialize query executor.

        Args:
            connection_pool: Database connection pool
            query_cache: Query result cache
            max_retries: Maximum number of retry attempts
            retry_delay_ms: Delay between retries in milliseconds
        """
        self.connection_pool = connection_pool or get_connection_pool()
        self.query_cache = query_cache or get_query_cache()
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms

    def execute_query_plan(self, query_plan: QueryPlan, semantic_layer=None) -> QueryResult:
        """
        Execute a QueryPlan (end-to-end).

        Args:
            query_plan: Structured query plan
            semantic_layer: Optional semantic layer to use for SQL generation

        Returns:
            QueryResult with data and metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        # Generate SQL from QueryPlan
        sql = build_sql(query_plan, semantic_layer=semantic_layer)

        # Validate SQL for security
        is_valid, errors = validate_sql(sql)
        if not is_valid:
            # Auto-correct common issues before failing
            sql_corrected = sql
            corrections_made = []
            
            # Auto-fix: Add LIMIT clause if missing
            if "Query must include a LIMIT clause" in errors:
                # Add default LIMIT 100 at the end
                sql_corrected = sql.rstrip()
                if sql_corrected.endswith(';'):
                    sql_corrected = sql_corrected[:-1].rstrip()
                sql_corrected += " LIMIT 100"
                corrections_made.append("Added LIMIT 100")
                
                # Re-validate
                is_valid, errors = validate_sql(sql_corrected)
                if is_valid:
                    sql = sql_corrected
                    logger.info(f"Auto-corrected SQL: {', '.join(corrections_made)}")
            
            # If still invalid after corrections, raise error
            if not is_valid:
                raise QueryExecutionError(f"SQL validation failed: {', '.join(errors)}")

        # Execute SQL
        return self.execute_sql(sql)

    def execute_sql(self, sql: str) -> QueryResult:
        """
        Execute raw SQL query.

        Args:
            sql: SQL query string

        Returns:
            QueryResult with data and metadata

        Raises:
            QueryExecutionError: If query execution fails after retries
        """
        # Check cache first
        cached_result = self.query_cache.get(sql)
        if cached_result is not None:
            return QueryResult(
                rows=cached_result,
                row_count=len(cached_result),
                execution_time_ms=0.0,
                from_cache=True,
            )

        # Execute with retries
        for attempt in range(self.max_retries):
            try:
                result = self._execute_with_timing(sql)

                # Cache successful result
                self.query_cache.set(sql, result.rows)

                return result

            except psycopg2.OperationalError as e:
                # Retry on operational errors (connection issues, etc.)
                if attempt < self.max_retries - 1:
                    delay_s = self.retry_delay_ms / 1000.0 * (2**attempt)
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {delay_s}s: {e}"
                    )
                    time.sleep(delay_s)
                else:
                    logger.error(f"Query failed after {self.max_retries} attempts: {e}")
                    raise QueryExecutionError(
                        f"Query execution failed after {self.max_retries} retries"
                    ) from e

            except psycopg2.Error as e:
                # Don't retry on SQL errors (syntax, permission, etc.)
                logger.error(f"SQL error: {e}")
                raise QueryExecutionError(f"SQL error: {e}") from e

            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error during query execution: {e}")
                raise QueryExecutionError(f"Unexpected error: {e}") from e

        raise QueryExecutionError("Query execution failed (max retries exceeded)")

    def _execute_with_timing(self, sql: str) -> QueryResult:
        """
        Execute SQL and measure timing.

        Args:
            sql: SQL query string

        Returns:
            QueryResult with timing information
        """
        start_time = time.perf_counter()

        with self.connection_pool.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

                # Convert RealDictRow to regular dict
                result_rows = [dict(row) for row in rows]

        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000

        logger.info(
            f"Query executed in {execution_time_ms:.2f}ms, "
            f"returned {len(result_rows)} rows"
        )

        return QueryResult(
            rows=result_rows,
            row_count=len(result_rows),
            execution_time_ms=execution_time_ms,
            from_cache=False,
        )

    def execute_batch(self, query_plans: List[QueryPlan]) -> List[QueryResult]:
        """
        Execute multiple query plans in sequence.

        Args:
            query_plans: List of query plans to execute

        Returns:
            List of query results
        """
        results = []
        for i, plan in enumerate(query_plans):
            logger.info(f"Executing query {i + 1}/{len(query_plans)}")
            try:
                result = self.execute_query_plan(plan)
                results.append(result)
            except Exception as e:
                logger.error(f"Query {i + 1} failed: {e}")
                # Continue with remaining queries
                results.append(
                    QueryResult(
                        rows=[],
                        row_count=0,
                        execution_time_ms=0.0,
                        from_cache=False,
                    )
                )

        return results


# Convenience function
def execute_query(query_plan: QueryPlan, semantic_layer=None, connection_id: Optional[str] = None) -> QueryResult:
    """
    Execute a query plan (convenience function).

    Args:
        query_plan: Structured query plan
        semantic_layer: Optional semantic layer to use for SQL generation
        connection_id: Optional connection ID to execute query against (if None, uses internal DB)

    Returns:
        QueryResult with data and metadata
    """
    if connection_id:
        # Execute on specific connection
        from src.connection.manager import get_connection_manager
        manager = get_connection_manager()
        conn = manager.get_connection(connection_id)
        
        # Generate SQL
        sql = build_sql(query_plan, semantic_layer=semantic_layer)
        
        # Validate SQL
        is_valid, errors = validate_sql(sql)
        if not is_valid:
            # Auto-fix: Add LIMIT clause if missing
            if "Query must include a LIMIT clause" in errors:
                sql_corrected = sql.rstrip()
                if sql_corrected.endswith(';'):
                    sql_corrected = sql_corrected[:-1].rstrip()
                sql_corrected += " LIMIT 100"
                is_valid, errors = validate_sql(sql_corrected)
                if is_valid:
                    sql = sql_corrected
            
            if not is_valid:
                raise QueryExecutionError(f"SQL validation failed: {', '.join(errors)}")
        
        # Execute query on specific connection
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            start_time = time.time()
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            execution_time = (time.time() - start_time) * 1000
            cursor.close()
            
            return QueryResult(
                rows=rows,
                row_count=len(rows),
                execution_time_ms=execution_time,
                from_cache=False,
                sql=sql
            )
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"SQL: {sql}")
            raise QueryExecutionError(f"SQL error: {str(e)}")
    else:
        # Execute on internal database
        executor = QueryExecutor()
        return executor.execute_query_plan(query_plan, semantic_layer=semantic_layer)
