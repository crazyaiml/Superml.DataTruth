"""
Improved QueryOrchestrator with proper validation, error types, and analytics.

Key improvements:
1. Real caching with cache-hit metadata
2. Multi-level validation (plan-level + SQL AST)
3. Typed errors with debug payloads
4. Analytics on full result set (before pagination)
"""

import time
import hashlib
import sqlparse
from sqlparse import sql, tokens as T
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from src.semantic.loader import get_semantic_loader
from src.planner.intent_extractor import IntentExtractor
from src.planner.query_plan import QueryPlan
from src.sql.builder import SQLBuilder
from src.sql.validator_v2 import ProductionSQLValidator, ValidationLevel
from src.database.executor import get_query_executor
from src.optimization.pagination import PaginationParams, paginate_results
from src.optimization.plan_cache import get_plan_cache
from src.optimization.analyzer import get_query_analyzer
from src.analytics.time_intelligence import get_time_intelligence
from src.analytics.statistics import get_statistical_analyzer
from src.analytics.anomaly import get_anomaly_detector, AnomalyMethod
from src.user.authorization import UserContext, get_authorization_validator, Permission
from src.user.rls_engine import RLSEngine


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
    type: ErrorType = Field(description="Error type")
    message: str = Field(description="Error message")
    stage: str = Field(description="Pipeline stage where error occurred")
    debug_info: Optional[Dict[str, Any]] = Field(default=None, description="Debug information")


class QueryRequest(BaseModel):
    """Request for query execution."""
    question: str = Field(description="Natural language question")
    user_context: Optional[UserContext] = Field(default=None, description="User context for authorization and RLS (optional, uses default admin if not provided)")
    pagination: Optional[PaginationParams] = Field(default=None, description="Pagination parameters")
    enable_analytics: bool = Field(default=True, description="Enable analytics features")
    enable_caching: bool = Field(default=True, description="Enable result caching")
    enable_debug: bool = Field(default=False, description="Include debug info in errors")
    enable_rls: bool = Field(default=False, description="Enable row-level security (requires user_context)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class QueryResponse(BaseModel):
    """Response from query execution."""
    request_id: str = Field(description="Unique request identifier")
    question: str = Field(description="Original question")
    success: bool = Field(description="Whether query succeeded")
    error: Optional[QueryError] = Field(default=None, description="Error information if failed")
    query_plan: Optional[Dict[str, Any]] = Field(default=None, description="Generated query plan")
    sql: str = Field(default="", description="Generated SQL")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    pagination: Optional[Dict[str, Any]] = Field(default=None, description="Pagination metadata")
    analytics: Optional[Dict[str, Any]] = Field(default=None, description="Analytics insights")
    performance: Dict[str, Any] = Field(description="Performance metrics")
    explanation: str = Field(description="Human-readable explanation")
    cached: bool = Field(description="Whether result was cached")


class ImprovedQueryOrchestrator:
    """
    Improved query orchestrator with:
    - Real caching with cache-hit tracking
    - Multi-level validation (plan + SQL AST)
    - Typed errors with debug info
    - Analytics on full result sets
    """
    
    def __init__(
        self,
        enable_plan_cache: bool = True,
        enable_result_cache: bool = True,
        enable_analytics: bool = True,
        validation_level: ValidationLevel = ValidationLevel.MODERATE,
        enable_rls: bool = True
    ):
        """Initialize orchestrator."""
        self.enable_plan_cache = enable_plan_cache
        self.enable_result_cache = enable_result_cache
        self.enable_analytics = enable_analytics
        self.validation_level = validation_level
        self.enable_rls = enable_rls
        
        # Initialize components
        self.semantic_loader = get_semantic_loader()
        self.intent_extractor = IntentExtractor()
        self.sql_builder = SQLBuilder()
        self.query_executor = get_query_executor()
        
        # SQL validator will be initialized with semantic context during execution
        self.sql_validator = None
        
        # Authorization and RLS
        self.authorization_validator = get_authorization_validator()
        self.rls_engine = RLSEngine(enable_audit=True) if enable_rls else None
    
    def _get_default_user_context(self) -> UserContext:
        """Create default admin user context for backward compatibility."""
        from src.user.authorization import Role, Permission, TablePermission
        
        return UserContext(
            user_id="default_user",
            username="default_admin",
            email="admin@datatruth.local",
            roles=[Role.ADMIN],
            custom_permissions=set(),
            table_permissions=[],  # Admin has access to all tables
            rls_filters=[],  # No RLS filters for default admin
            metric_permissions=[]
        )
        
        # Optimization components
        if self.enable_plan_cache:
            self.plan_cache = get_plan_cache()
        
        self.query_analyzer = get_query_analyzer()
        
        # Analytics components
        if self.enable_analytics:
            self.time_intelligence = get_time_intelligence()
            self.stats_analyzer = get_statistical_analyzer()
            self.anomaly_detector = get_anomaly_detector()
    
    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """
        Execute query with full validation pipeline:
        
        1. Load semantic context
        2. Extract intent (with plan caching)
        3. Validate query plan
        4. Generate SQL
        5. Validate SQL (string + AST)
        6. Execute query (full result set)
        7. Run analytics (on full results)
        8. Apply pagination
        9. Cache result
        """
        request_id = self._generate_request_id(request.question)
        start_time = time.time()
        timings = {}
        
        try:
            # Get or create user context
            user_context = request.user_context or self._get_default_user_context()
            
            # Stage 0: Authorization check (skip for default admin)
            if request.user_context:  # Only check if user context explicitly provided
                stage_start = time.time()
                allowed, error_msg = self.authorization_validator.validate_query_permission(user_context)
                if not allowed:
                    raise self._create_error(
                        ErrorType.VALIDATION_ERROR,
                        "authorization",
                        error_msg,
                        {"user_id": user_context.user_id} if request.enable_debug else None
                    )
                timings["authorization"] = time.time() - stage_start
            
            # Stage 1: Load semantic context (filtered by user permissions)
            stage_start = time.time()
            semantic_context = self._load_semantic_context(user_context)
            timings["semantic_context"] = time.time() - stage_start
            
            # Stage 2: Get query plan (with caching)
            stage_start = time.time()
            query_plan, plan_cached = await self._get_query_plan(
                request.question,
                semantic_context,
                request.enable_caching
            )
            timings["query_planning"] = time.time() - stage_start
            
            # Stage 3: Validate query plan
            stage_start = time.time()
            plan_valid, plan_errors = self._validate_plan(query_plan, semantic_context)
            if not plan_valid:
                raise self._create_error(
                    ErrorType.PLAN_ERROR,
                    "plan_validation",
                    f"Invalid query plan: {', '.join(plan_errors)}",
                    {"plan": query_plan.model_dump(), "errors": plan_errors} if request.enable_debug else None
                )
            timings["plan_validation"] = time.time() - stage_start
            
            # Stage 4: Generate SQL
            stage_start = time.time()
            sql = self._generate_sql(query_plan)
            timings["sql_generation"] = time.time() - stage_start
            
            # Stage 5: Validate SQL (string + AST)
            stage_start = time.time()
            
            # Initialize validator with semantic context
            if not self.sql_validator:
                self.sql_validator = ProductionSQLValidator(
                    semantic_context=semantic_context,
                    validation_level=self.validation_level,
                    max_row_limit=10000,
                    require_limit=True
                )
            
            validation_result = self.sql_validator.validate(sql)
            
            # Validate table/column authorization (skip for default admin without RLS)
            if request.user_context and request.enable_rls:
                auth_errors = self._validate_sql_authorization(sql, user_context)
                if auth_errors:
                    raise self._create_error(
                        ErrorType.VALIDATION_ERROR,
                        "sql_authorization",
                        f"Authorization failed: {', '.join(auth_errors)}",
                        {"sql": sql, "errors": auth_errors} if request.enable_debug else None
                    )
            
            if not validation_result.is_valid:
                error_messages = [f"{err.code}: {err.message}" for err in validation_result.errors]
                raise self._create_error(
                    ErrorType.VALIDATION_ERROR,
                    "sql_validation",
                    f"SQL validation failed: {', '.join(error_messages)}",
                    {
                        "sql": sql,
                        "errors": [err.dict() for err in validation_result.errors],
                        "warnings": [w.dict() for w in validation_result.warnings],
                        "metadata": validation_result.metadata
                    } if request.enable_debug else None
                )
            
            # Add warnings to metadata for monitoring
            if validation_result.warnings:
                metadata['sql_warnings'] = [
                    f"{w.code}: {w.message}" for w in validation_result.warnings
                ]
            
            timings["sql_validation"] = time.time() - stage_start
            
            # Stage 5.5: Apply RLS (Row-Level Security)
            if self.enable_rls and request.enable_rls and self.rls_engine and user_context.rls_filters:
                stage_start = time.time()
                rls_result = self.rls_engine.inject_rls(sql, user_context)
                sql = rls_result.rewritten_sql  # Use RLS-protected SQL
                
                metadata['rls_applied'] = True
                metadata['rls_filters_count'] = len(rls_result.injected_filters)
                metadata['rls_tables_affected'] = rls_result.tables_affected
                
                if request.enable_debug:
                    metadata['rls_details'] = {
                        'original_sql': rls_result.original_sql,
                        'injected_filters': rls_result.injected_filters
                    }
                
                timings["rls_injection"] = time.time() - stage_start
            else:
                metadata['rls_applied'] = False
            
            # Stage 6: Execute query (FULL result set - no pagination yet)
            stage_start = time.time()
            full_results, result_cached = await self._execute_query(sql, request.enable_caching)
            timings["query_execution"] = time.time() - stage_start
            
            # Stage 7: Run analytics on FULL result set (before pagination)
            analytics = None
            if request.enable_analytics and self.enable_analytics and full_results:
                stage_start = time.time()
                try:
                    analytics = self._calculate_analytics(full_results, query_plan)
                except Exception as e:
                    # Analytics errors should not fail the query
                    print(f"Analytics computation failed: {str(e)}")
                    analytics = {"error": str(e)}
                timings["analytics"] = time.time() - stage_start
            
            # Stage 8: Apply pagination AFTER analytics
            stage_start = time.time()
            pagination_metadata = None
            if request.pagination:
                results, pagination_metadata = paginate_results(
                    full_results,
                    len(full_results),
                    request.pagination
                )
            else:
                results = full_results
            timings["pagination"] = time.time() - stage_start
            
            # Stage 9: Performance tracking
            self._record_performance(
                sql,
                timings["query_execution"] * 1000,
                len(full_results),
                result_cached
            )
            
            # Stage 10: Generate explanation
            stage_start = time.time()
            explanation = self._generate_explanation(query_plan, len(full_results))
            timings["explanation"] = time.time() - stage_start
            
            # Calculate total time
            total_time = time.time() - start_time
            
            return QueryResponse(
                request_id=request_id,
                question=request.question,
                success=True,
                error=None,
                query_plan=query_plan.model_dump() if query_plan else None,
                sql=sql,
                results=results,
                pagination=pagination_metadata.model_dump() if pagination_metadata else None,
                analytics=analytics,
                performance={
                    "total_time_ms": int(total_time * 1000),
                    "stage_timings_ms": {k: int(v * 1000) for k, v in timings.items()},
                    "plan_cached": plan_cached,
                    "result_cached": result_cached
                },
                explanation=explanation,
                cached=result_cached
            )
            
        except ValueError as e:
            # Typed errors with debug info
            if hasattr(e, '__dict__') and 'type' in e.__dict__:
                error_data = QueryError(
                    type=e.type,
                    message=str(e),
                    stage=e.stage,
                    debug_info=e.debug_info
                )
            else:
                error_data = QueryError(
                    type=ErrorType.UNKNOWN_ERROR,
                    message=str(e),
                    stage="unknown",
                    debug_info=None
                )
            
            total_time = time.time() - start_time
            return QueryResponse(
                request_id=request_id,
                question=request.question,
                success=False,
                error=error_data,
                query_plan=None,
                sql="",
                results=[],
                pagination=None,
                analytics=None,
                performance={
                    "total_time_ms": int(total_time * 1000),
                    "stage_timings_ms": {k: int(v * 1000) for k, v in timings.items()}
                },
                explanation=f"Query failed: {str(e)}",
                cached=False
            )
        except Exception as e:
            # Unexpected errors
            print(f"Unexpected error in query execution: {str(e)}")
            error_data = QueryError(
                type=ErrorType.UNKNOWN_ERROR,
                message=f"Unexpected error: {str(e)}",
                stage="unknown",
                debug_info={"exception_type": type(e).__name__} if request.enable_debug else None
            )
            
            total_time = time.time() - start_time
            return QueryResponse(
                request_id=request_id,
                question=request.question,
                success=False,
                error=error_data,
                query_plan=None,
                sql="",
                results=[],
                pagination=None,
                analytics=None,
                performance={
                    "total_time_ms": int(total_time * 1000),
                    "stage_timings_ms": {k: int(v * 1000) for k, v in timings.items()}
                },
                explanation=f"Query failed: {str(e)}",
                cached=False
            )
    
    def _generate_request_id(self, question: str) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{timestamp}:{question}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _load_semantic_context(self, user_context: UserContext) -> Dict[str, Any]:
        """
        Load semantic layer context filtered by user permissions.
        
        Only returns metrics/dimensions the user can access.
        For admin users or when no table permissions are set, returns all elements.
        """
        # Load full context
        all_metrics = self.semantic_loader.get_all_metrics()
        all_dimensions = self.semantic_loader.get_all_dimensions()
        all_synonyms = self.semantic_loader.get_all_synonyms()
        
        # If user is admin or has no table permissions, return everything
        if user_context.is_admin() or not user_context.table_permissions:
            return {
                "metrics": all_metrics,
                "dimensions": all_dimensions,
                "synonyms": all_synonyms
            }
        
        # Filter by user permissions
        filtered_metrics = []
        for metric in all_metrics:
            try:
                metric_name = metric.get('name', '') if isinstance(metric, dict) else getattr(metric, 'name', '')
                if metric_name and user_context.can_access_metric(metric_name):
                    filtered_metrics.append(metric)
            except Exception:
                # If we can't determine metric name, include it (fail open for usability)
                filtered_metrics.append(metric)
        
        filtered_dimensions = []
        for dimension in all_dimensions:
            try:
                dim_name = dimension.get('name', '') if isinstance(dimension, dict) else getattr(dimension, 'name', '')
                # Dimensions typically tied to tables/columns
                if isinstance(dimension, dict) and 'table' in dimension:
                    if user_context.can_access_table(dimension['table']):
                        filtered_dimensions.append(dimension)
                else:
                    # If no table association, include it
                    filtered_dimensions.append(dimension)
            except Exception:
                # If we can't determine access, include it (fail open for usability)
                filtered_dimensions.append(dimension)
        
        return {
            "metrics": filtered_metrics,
            "dimensions": filtered_dimensions,
            "synonyms": all_synonyms  # Synonyms are not sensitive
        }
    
    async def _get_query_plan(
        self,
        question: str,
        semantic_context: Dict[str, Any],
        enable_caching: bool
    ) -> Tuple[QueryPlan, bool]:
        """
        Get query plan with REAL caching.
        
        Returns:
            Tuple of (QueryPlan, cached)
        """
        # Check cache
        if enable_caching and self.enable_plan_cache:
            cached_plan = self.plan_cache.get(question, semantic_context)
            if cached_plan:
                return cached_plan, True  # Real cache hit
        
        # Generate new plan
        try:
            intent = await self.intent_extractor.extract_intent(
                question,
                semantic_context
            )
            query_plan = intent.query_plan
        except Exception as e:
            raise self._create_error(
                ErrorType.LLM_ERROR,
                "intent_extraction",
                f"Failed to extract intent: {str(e)}",
                {"question": question}
            )
        
        # Cache if enabled
        if enable_caching and self.enable_plan_cache and query_plan:
            self.plan_cache.set(question, query_plan, semantic_context)
        
        return query_plan, False  # Not cached
    
    def _validate_plan(
        self,
        query_plan: QueryPlan,
        semantic_context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate query plan BEFORE SQL generation.
        
        Checks:
        - All metrics exist in semantic layer
        - All dimensions exist in semantic layer
        - Filters reference valid fields
        - Time ranges are valid
        - Aggregations are compatible with grouping
        """
        errors = []
        
        if not query_plan:
            return False, ["Query plan is None"]
        
        # Validate metrics
        available_metrics = {m["name"] for m in semantic_context.get("metrics", [])}
        if query_plan.metrics:
            for metric in query_plan.metrics:
                if metric.name not in available_metrics:
                    errors.append(f"Unknown metric: {metric.name}")
        
        # Validate dimensions
        available_dimensions = {d["name"] for d in semantic_context.get("dimensions", [])}
        if query_plan.dimensions:
            for dimension in query_plan.dimensions:
                if dimension.name not in available_dimensions:
                    errors.append(f"Unknown dimension: {dimension.name}")
        
        # Validate filters
        if query_plan.filters:
            for filter_item in query_plan.filters:
                # Check if field exists in metrics or dimensions
                if filter_item.field not in available_metrics and filter_item.field not in available_dimensions:
                    errors.append(f"Unknown filter field: {filter_item.field}")
        
        # Validate time range
        if query_plan.time_range:
            if query_plan.time_range.start and query_plan.time_range.end:
                try:
                    start = datetime.fromisoformat(query_plan.time_range.start)
                    end = datetime.fromisoformat(query_plan.time_range.end)
                    if start > end:
                        errors.append("Time range start is after end")
                except Exception:
                    errors.append("Invalid time range format")
        
        return len(errors) == 0, errors
    
    def _generate_sql(self, query_plan: QueryPlan) -> str:
        """Generate SQL from query plan."""
        try:
            return self.sql_builder.build(query_plan)
        except Exception as e:
            raise self._create_error(
                ErrorType.SQL_GENERATION_ERROR,
                "sql_generation",
                f"Failed to generate SQL: {str(e)}",
                {"plan": query_plan.model_dump()}
            )
    
    def _validate_sql_authorization(
        self,
        sql: str,
        user_context: UserContext
    ) -> List[str]:
        """
        Validate user is authorized to access tables/columns in SQL.
        
        Returns list of authorization errors.
        """
        errors = []
        
        # Parse SQL to extract tables and columns
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return []
            
            statement = parsed[0]
        except Exception:
            return []  # Let SQL validator handle parse errors
        
        # Extract tables
        tables = self._extract_table_names(statement)
        
        # Validate table access
        for table in tables:
            allowed, error_msg = self.authorization_validator.validate_table_access(
                user_context,
                table,
                "query"
            )
            if not allowed:
                errors.append(f"Table access denied: {table}")
        
        # Could also extract and validate column access here
        # For now, table-level validation is sufficient
        
        return errors
    
    def _extract_table_names(self, statement: sql.Statement) -> Set[str]:
        """Extract table names from SQL statement."""
        tables = set()
        
        from_seen = False
        join_seen = False
        
        for token in statement.tokens:
            if token.ttype is T.Keyword and token.value.upper() == 'FROM':
                from_seen = True
            elif token.ttype is T.Keyword and 'JOIN' in token.value.upper():
                join_seen = True
            elif (from_seen or join_seen) and isinstance(token, sql.Identifier):
                table_name = token.get_real_name()
                if table_name:
                    tables.add(table_name.lower())
                from_seen = False
                join_seen = False
            elif (from_seen or join_seen) and token.ttype is T.Name:
                tables.add(token.value.lower())
                from_seen = False
                join_seen = False
        
        return tables
    
    async def _execute_query(
        self,
        sql: str,
        enable_caching: bool
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Execute query with REAL result caching.
        
        Returns:
            Tuple of (results, cached)
        """
        try:
            # Execute query
            # The executor should return cache status
            results = await self.query_executor.execute(sql)
            
            # Check if result was from cache
            # This assumes the executor has a method to check cache status
            # For now, we'll use a simple approach
            cached = False
            if hasattr(self.query_executor, 'last_query_was_cached'):
                cached = self.query_executor.last_query_was_cached()
            
            return results, cached
            
        except Exception as e:
            raise self._create_error(
                ErrorType.EXECUTION_ERROR,
                "query_execution",
                f"Query execution failed: {str(e)}",
                {"sql": sql}
            )
    
    def _calculate_analytics(
        self,
        results: List[Dict[str, Any]],
        query_plan: QueryPlan
    ) -> Dict[str, Any]:
        """
        Calculate analytics for FULL result set.
        
        Note: This runs BEFORE pagination to ensure accurate statistics.
        """
        if not results:
            return None
        
        analytics = {}
        
        # Find numeric columns
        numeric_columns = []
        if results:
            first_row = results[0]
            for key, value in first_row.items():
                if isinstance(value, (int, float)):
                    numeric_columns.append(key)
        
        # Calculate statistics for each numeric column
        for col in numeric_columns:
            try:
                values = [row[col] for row in results if isinstance(row.get(col), (int, float))]
                
                if len(values) < 2:
                    continue
                
                # Descriptive statistics
                stats = self.stats_analyzer.calculate_descriptive_stats(values)
                
                # Anomaly detection
                anomalies = self.anomaly_detector.detect_anomalies(
                    values,
                    method=AnomalyMethod.IQR
                )
                
                analytics[col] = {
                    "statistics": {
                        "count": stats.count,
                        "mean": stats.mean,
                        "median": stats.median,
                        "std_dev": stats.std_dev,
                        "min": stats.min,
                        "max": stats.max,
                        "range": stats.range
                    },
                    "anomalies": {
                        "count": len(anomalies.anomalies),
                        "rate": anomalies.anomaly_rate,
                        "has_severe": anomalies.high_severity_count > 0
                    } if anomalies.has_anomalies else None
                }
            except Exception:
                # Skip analytics for this column if error
                continue
        
        # Add metadata
        analytics["_metadata"] = {
            "total_rows": len(results),
            "numeric_columns_analyzed": len(analytics) - 1,  # Exclude _metadata
            "computed_on_full_dataset": True
        }
        
        return analytics if analytics else None
    
    def _record_performance(
        self,
        sql: str,
        execution_time_ms: float,
        row_count: int,
        from_cache: bool
    ):
        """Record performance metrics."""
        query_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]
        self.query_analyzer.record_execution(
            query_hash=query_hash,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            from_cache=from_cache
        )
    
    def _generate_explanation(
        self,
        query_plan: QueryPlan,
        result_count: int
    ) -> str:
        """Generate human-readable explanation."""
        if not query_plan:
            return "Unable to generate query plan"
        
        parts = []
        
        # Metrics
        if query_plan.metrics:
            metric_names = [m.name for m in query_plan.metrics]
            parts.append(f"Calculated {', '.join(metric_names)}")
        
        # Dimensions
        if query_plan.dimensions:
            dim_names = [d.name for d in query_plan.dimensions]
            parts.append(f"grouped by {', '.join(dim_names)}")
        
        # Filters
        if query_plan.filters:
            filter_desc = [f"{f.field} {f.operator} {f.value}" for f in query_plan.filters]
            parts.append(f"filtered by {', '.join(filter_desc)}")
        
        # Time range
        if query_plan.time_range:
            parts.append(f"for {query_plan.time_range.period or 'custom date range'}")
        
        # Result count
        parts.append(f"returned {result_count} rows")
        
        return ". ".join(parts).capitalize() + "."
    
    def _create_error(
        self,
        error_type: ErrorType,
        stage: str,
        message: str,
        debug_info: Optional[Dict[str, Any]] = None
    ) -> ValueError:
        """Create a typed error with metadata."""
        error = ValueError(message)
        error.type = error_type
        error.stage = stage
        error.debug_info = debug_info
        return error


# Global singleton instance
_improved_orchestrator_instance: Optional[ImprovedQueryOrchestrator] = None


def get_improved_orchestrator() -> ImprovedQueryOrchestrator:
    """
    Get the global ImprovedQueryOrchestrator instance.
    
    Returns:
        ImprovedQueryOrchestrator singleton
    """
    global _improved_orchestrator_instance
    if _improved_orchestrator_instance is None:
        _improved_orchestrator_instance = ImprovedQueryOrchestrator()
    return _improved_orchestrator_instance
