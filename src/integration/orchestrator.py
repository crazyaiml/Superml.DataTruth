"""
End-to-end query orchestrator for DataTruth.

Integrates all components: semantic layer, LLM, SQL generation, execution,
caching, optimization, and analytics into a unified pipeline.
"""

import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.semantic.loader import get_semantic_loader
from src.planner.intent_extractor import IntentExtractor
from src.planner.query_plan import QueryPlan
from src.sql.builder import SQLBuilder
from src.sql.validator import SQLValidator
from src.database.executor import get_query_executor
from src.optimization.pagination import PaginationParams, paginate_results
from src.optimization.plan_cache import get_plan_cache
from src.optimization.analyzer import get_query_analyzer
from src.analytics.time_intelligence import get_time_intelligence
from src.analytics.statistics import get_statistical_analyzer
from src.analytics.anomaly import get_anomaly_detector, AnomalyMethod


class QueryRequest(BaseModel):
    """Request for query execution."""
    question: str = Field(description="Natural language question")
    pagination: Optional[PaginationParams] = Field(default=None, description="Pagination parameters")
    enable_analytics: bool = Field(default=True, description="Enable analytics features")
    enable_caching: bool = Field(default=True, description="Enable result caching")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class QueryResponse(BaseModel):
    """Response from query execution."""
    request_id: str = Field(description="Unique request identifier")
    question: str = Field(description="Original question")
    query_plan: Optional[Dict[str, Any]] = Field(description="Generated query plan")
    sql: str = Field(description="Generated SQL")
    results: List[Dict[str, Any]] = Field(description="Query results")
    pagination: Optional[Dict[str, Any]] = Field(default=None, description="Pagination metadata")
    analytics: Optional[Dict[str, Any]] = Field(default=None, description="Analytics insights")
    performance: Dict[str, Any] = Field(description="Performance metrics")
    explanation: str = Field(description="Human-readable explanation")
    cached: bool = Field(description="Whether result was cached")


class QueryOrchestrator:
    """
    Orchestrates the complete query pipeline.
    
    Pipeline stages:
    1. Semantic layer loading
    2. Intent extraction (with plan caching)
    3. SQL generation
    4. SQL validation
    5. Query execution (with result caching)
    6. Analytics calculation
    7. Response formatting
    """
    
    def __init__(
        self,
        enable_plan_cache: bool = True,
        enable_result_cache: bool = True,
        enable_analytics: bool = True,
        enable_performance_tracking: bool = True
    ):
        """
        Initialize orchestrator.
        
        Args:
            enable_plan_cache: Enable query plan caching
            enable_result_cache: Enable result caching
            enable_analytics: Enable analytics features
            enable_performance_tracking: Enable performance tracking
        """
        self.enable_plan_cache = enable_plan_cache
        self.enable_result_cache = enable_result_cache
        self.enable_analytics = enable_analytics
        self.enable_performance_tracking = enable_performance_tracking
        
        # Initialize components
        self.semantic_loader = get_semantic_loader()
        self.intent_extractor = IntentExtractor()
        self.sql_builder = SQLBuilder()
        self.sql_validator = SQLValidator()
        self.query_executor = get_query_executor()
        
        # Optimization components
        if self.enable_plan_cache:
            self.plan_cache = get_plan_cache()
        
        if self.enable_performance_tracking:
            self.query_analyzer = get_query_analyzer()
        
        # Analytics components
        if self.enable_analytics:
            self.time_intelligence = get_time_intelligence()
            self.stats_analyzer = get_statistical_analyzer()
            self.anomaly_detector = get_anomaly_detector()
    
    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """
        Execute a natural language query end-to-end.
        
        Args:
            request: Query request
        
        Returns:
            Query response with results and analytics
        """
        request_id = self._generate_request_id(request.question)
        start_time = time.time()
        
        performance = {
            "total_time_ms": 0,
            "plan_time_ms": 0,
            "sql_time_ms": 0,
            "execution_time_ms": 0,
            "analytics_time_ms": 0,
            "plan_cached": False,
            "result_cached": False
        }
        
        try:
            # Stage 1: Load semantic layer context
            semantic_context = self._load_semantic_context()
            
            # Stage 2: Intent extraction with plan caching
            plan_start = time.time()
            query_plan, plan_cached = await self._get_query_plan(
                request.question,
                semantic_context,
                request.enable_caching
            )
            performance["plan_time_ms"] = (time.time() - plan_start) * 1000
            performance["plan_cached"] = plan_cached
            
            # Stage 3: SQL generation
            sql_start = time.time()
            sql = self._generate_sql(query_plan)
            performance["sql_time_ms"] = (time.time() - sql_start) * 1000
            
            # Stage 4: SQL validation
            validation_errors = self.sql_validator.validate(sql)
            if validation_errors:
                raise ValueError(f"SQL validation failed: {validation_errors}")
            
            # Stage 5: Query execution with result caching
            exec_start = time.time()
            results, result_cached = await self._execute_query(
                sql,
                request.enable_caching
            )
            performance["execution_time_ms"] = (time.time() - exec_start) * 1000
            performance["result_cached"] = result_cached
            
            # Stage 6: Pagination
            pagination_metadata = None
            if request.pagination:
                results, pagination_metadata = paginate_results(
                    results,
                    len(results),
                    request.pagination
                )
            
            # Stage 7: Analytics
            analytics = None
            if request.enable_analytics and self.enable_analytics:
                analytics_start = time.time()
                analytics = self._calculate_analytics(results, query_plan)
                performance["analytics_time_ms"] = (time.time() - analytics_start) * 1000
            
            # Stage 8: Performance tracking
            if self.enable_performance_tracking:
                self._record_performance(
                    sql,
                    performance["execution_time_ms"],
                    len(results),
                    result_cached
                )
            
            # Stage 9: Generate explanation
            explanation = self._generate_explanation(query_plan, len(results))
            
            # Calculate total time
            performance["total_time_ms"] = (time.time() - start_time) * 1000
            
            return QueryResponse(
                request_id=request_id,
                question=request.question,
                query_plan=query_plan.model_dump() if query_plan else None,
                sql=sql,
                results=results,
                pagination=pagination_metadata.model_dump() if pagination_metadata else None,
                analytics=analytics,
                performance=performance,
                explanation=explanation,
                cached=result_cached
            )
            
        except Exception as e:
            # Record error
            performance["total_time_ms"] = (time.time() - start_time) * 1000
            
            # Return error response
            return QueryResponse(
                request_id=request_id,
                question=request.question,
                query_plan=None,
                sql="",
                results=[],
                pagination=None,
                analytics=None,
                performance=performance,
                explanation=f"Error: {str(e)}",
                cached=False
            )
    
    def _generate_request_id(self, question: str) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{timestamp}:{question}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _load_semantic_context(self) -> Dict[str, Any]:
        """Load semantic layer context."""
        return {
            "metrics": self.semantic_loader.get_all_metrics(),
            "dimensions": self.semantic_loader.get_all_dimensions(),
            "synonyms": self.semantic_loader.get_all_synonyms()
        }
    
    async def _get_query_plan(
        self,
        question: str,
        semantic_context: Dict[str, Any],
        enable_caching: bool
    ) -> tuple[QueryPlan, bool]:
        """
        Get query plan with optional caching.
        
        Returns:
            Tuple of (QueryPlan, cached)
        """
        # Check cache
        if enable_caching and self.enable_plan_cache:
            cached_plan = self.plan_cache.get(question, semantic_context)
            if cached_plan:
                return cached_plan, True
        
        # Generate new plan
        intent = await self.intent_extractor.extract_intent(
            question,
            semantic_context
        )
        query_plan = intent.query_plan
        
        # Cache if enabled
        if enable_caching and self.enable_plan_cache and query_plan:
            self.plan_cache.set(question, query_plan, semantic_context)
        
        return query_plan, False
    
    def _generate_sql(self, query_plan: QueryPlan) -> str:
        """Generate SQL from query plan."""
        return self.sql_builder.build(query_plan)
    
    async def _execute_query(
        self,
        sql: str,
        enable_caching: bool
    ) -> tuple[List[Dict[str, Any]], bool]:
        """
        Execute query with optional result caching.
        
        Returns:
            Tuple of (results, cached)
        """
        # For now, just execute directly
        # Result caching is handled by the executor
        results = await self.query_executor.execute(sql)
        
        # TODO: Check if result was from cache
        # This would require the executor to return cache status
        cached = False
        
        return results, cached
    
    def _calculate_analytics(
        self,
        results: List[Dict[str, Any]],
        query_plan: QueryPlan
    ) -> Dict[str, Any]:
        """Calculate analytics for results."""
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


# Global singleton instance
_orchestrator_instance: Optional[QueryOrchestrator] = None


def get_orchestrator() -> QueryOrchestrator:
    """
    Get the global QueryOrchestrator instance.
    
    Returns:
        QueryOrchestrator singleton
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = QueryOrchestrator()
    return _orchestrator_instance
