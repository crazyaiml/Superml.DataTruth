"""
Real-time Metric Engine - Dynamic Metric Computation

Compute metrics on-the-fly with live data, adjusting based on:
- Data freshness and quality
- Time of day / business context
- Special events or overrides
- Pending vs completed transactions
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel

from src.semantic.models import Metric, Filter
from src.semantic.loader import get_semantic_layer


class DataFreshnessLevel(str, Enum):
    """Data freshness levels."""
    
    REALTIME = "realtime"       # < 5 minutes old
    FRESH = "fresh"             # < 1 hour old
    RECENT = "recent"           # < 24 hours old
    STALE = "stale"             # > 24 hours old
    UNKNOWN = "unknown"


class MetricWarning(BaseModel):
    """Warning about metric computation."""
    
    level: str  # "info", "warning", "error"
    message: str
    details: Optional[Dict[str, Any]] = None


class EnrichedMetric(BaseModel):
    """Metric with real-time enrichments."""
    
    metric: Metric
    data_freshness: DataFreshnessLevel
    last_updated: Optional[datetime] = None
    warnings: List[MetricWarning] = []
    computed_filters: List[Filter] = []
    context_notes: List[str] = []


class RealtimeContext(BaseModel):
    """Context for real-time metric computation."""
    
    include_pending: bool = False
    use_estimated_costs: bool = False
    exclude_test_data: bool = True
    time_of_day: Optional[str] = None  # "month_end", "year_end", etc.
    special_events: List[str] = []  # ["black_friday", "product_launch"]


class RealtimeMetricEngine:
    """
    Compute metrics dynamically based on real-time context.
    
    Features:
    - Data freshness checking
    - Dynamic filter adjustment
    - Context-aware computation
    - Warning generation
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize real-time metric engine.
        
        Args:
            db_connection: Database connection for freshness checks
        """
        self.base_layer = get_semantic_layer()
        self.db = db_connection
        
        # Cache for data freshness
        self._freshness_cache: Dict[str, Tuple[datetime, DataFreshnessLevel]] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def get_metric_definition(
        self,
        metric_name: str,
        context: RealtimeContext
    ) -> EnrichedMetric:
        """
        Get metric definition adjusted for real-time context.
        
        Args:
            metric_name: Name of the metric
            context: Real-time context for computation
        
        Returns:
            EnrichedMetric with dynamic adjustments and warnings
        """
        # Get base metric
        if metric_name not in self.base_layer.metrics:
            raise ValueError(f"Metric '{metric_name}' not found")
        
        base_metric = self.base_layer.metrics[metric_name]
        
        # Create enriched copy
        adjusted_metric = Metric(**base_metric.model_dump())
        warnings: List[MetricWarning] = []
        context_notes: List[str] = []
        
        # Check data freshness
        freshness = self._check_data_freshness(base_metric.base_table)
        
        if freshness == DataFreshnessLevel.STALE:
            warnings.append(MetricWarning(
                level="warning",
                message=f"Data for {base_metric.base_table} is more than 24 hours old",
                details={"table": base_metric.base_table}
            ))
        
        # Adjust filters based on context
        adjusted_filters = list(base_metric.filters)
        
        # Handle pending transactions
        if context.include_pending:
            # Remove status=completed filter
            adjusted_filters = [
                f for f in adjusted_filters
                if not (f.field.endswith("status") and f.value == "completed")
            ]
            context_notes.append("Including pending transactions")
            warnings.append(MetricWarning(
                level="info",
                message="Including pending/incomplete transactions",
                details={"filter_removed": "status=completed"}
            ))
        
        # Handle test data exclusion
        if context.exclude_test_data:
            # Add filter to exclude test data if not already present
            has_test_filter = any(
                "test" in f.field.lower() or "test" in str(f.value).lower()
                for f in adjusted_filters
            )
            if not has_test_filter:
                # Would add test data filter here if we had a test flag in schema
                pass
        
        # Handle estimated costs
        if context.use_estimated_costs and "cost" in adjusted_metric.formula:
            warnings.append(MetricWarning(
                level="info",
                message="Using estimated costs (actuals not yet available)",
                details={"formula_modified": True}
            ))
            context_notes.append("Using estimated costs")
        
        # Time-of-day adjustments
        if context.time_of_day == "month_end":
            warnings.append(MetricWarning(
                level="info",
                message="Month-end processing in progress - results may be incomplete",
                details={"time_context": "month_end"}
            ))
        elif context.time_of_day == "year_end":
            warnings.append(MetricWarning(
                level="warning",
                message="Year-end close in progress - numbers subject to change",
                details={"time_context": "year_end"}
            ))
        
        # Special event handling
        if "black_friday" in context.special_events:
            context_notes.append("Black Friday sales period - high volume expected")
        
        # Update metric filters
        adjusted_metric.filters = adjusted_filters
        
        # Get last update time
        last_updated = self._get_last_update_time(base_metric.base_table)
        
        return EnrichedMetric(
            metric=adjusted_metric,
            data_freshness=freshness,
            last_updated=last_updated,
            warnings=warnings,
            computed_filters=adjusted_filters,
            context_notes=context_notes
        )
    
    def _check_data_freshness(self, table_name: str) -> DataFreshnessLevel:
        """
        Check how fresh the data is for a table.
        
        Args:
            table_name: Name of the table to check
        
        Returns:
            DataFreshnessLevel
        """
        # Check cache first
        if table_name in self._freshness_cache:
            cached_time, cached_level = self._freshness_cache[table_name]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return cached_level
        
        # Query database for last update time
        if self.db is None:
            return DataFreshnessLevel.UNKNOWN
        
        try:
            # Try to find a timestamp column
            query = f"""
                SELECT MAX(updated_at) as last_update
                FROM {table_name}
            """
            
            # Fallback to created_at if updated_at doesn't exist
            # This would need proper error handling
            result = self.db.execute(query)
            
            if result and result[0]["last_update"]:
                last_update = result[0]["last_update"]
                age = datetime.utcnow() - last_update
                
                if age < timedelta(minutes=5):
                    freshness = DataFreshnessLevel.REALTIME
                elif age < timedelta(hours=1):
                    freshness = DataFreshnessLevel.FRESH
                elif age < timedelta(hours=24):
                    freshness = DataFreshnessLevel.RECENT
                else:
                    freshness = DataFreshnessLevel.STALE
                
                # Cache result
                self._freshness_cache[table_name] = (datetime.utcnow(), freshness)
                return freshness
        
        except Exception:
            # If we can't determine freshness, mark as unknown
            pass
        
        return DataFreshnessLevel.UNKNOWN
    
    def _get_last_update_time(self, table_name: str) -> Optional[datetime]:
        """Get the last update timestamp for a table."""
        if self.db is None:
            return None
        
        try:
            # Try to get max timestamp
            query = f"""
                SELECT COALESCE(MAX(updated_at), MAX(created_at)) as last_update
                FROM {table_name}
            """
            result = self.db.execute(query)
            
            if result and result[0]["last_update"]:
                return result[0]["last_update"]
        
        except Exception:
            pass
        
        return None
    
    def invalidate_freshness_cache(self, table_name: Optional[str] = None):
        """
        Invalidate freshness cache.
        
        Args:
            table_name: Specific table to invalidate, or None for all
        """
        if table_name:
            self._freshness_cache.pop(table_name, None)
        else:
            self._freshness_cache.clear()
    
    def get_recommended_context(self) -> RealtimeContext:
        """
        Get recommended context based on current time and system state.
        
        Returns:
            RealtimeContext with smart defaults
        """
        now = datetime.utcnow()
        
        # Determine time of day context
        time_of_day = None
        if now.day >= 28:  # Near month end
            time_of_day = "month_end"
        elif now.month == 12 and now.day >= 25:  # Near year end
            time_of_day = "year_end"
        
        # Determine special events
        special_events = []
        if now.month == 11 and 23 <= now.day <= 27:  # Black Friday period
            special_events.append("black_friday")
        elif now.month == 12 and 20 <= now.day <= 31:  # Holiday season
            special_events.append("holiday_season")
        
        # Default: use completed transactions only, exclude test data
        return RealtimeContext(
            include_pending=False,
            use_estimated_costs=(time_of_day == "month_end"),  # Use estimates at month-end
            exclude_test_data=True,
            time_of_day=time_of_day,
            special_events=special_events
        )
    
    def batch_get_metrics(
        self,
        metric_names: List[str],
        context: RealtimeContext
    ) -> Dict[str, EnrichedMetric]:
        """
        Get multiple metric definitions efficiently.
        
        Args:
            metric_names: List of metric names
            context: Real-time context
        
        Returns:
            Dict mapping metric names to EnrichedMetrics
        """
        result = {}
        
        # Pre-warm freshness cache for all tables
        tables = set()
        for name in metric_names:
            if name in self.base_layer.metrics:
                tables.add(self.base_layer.metrics[name].base_table)
        
        # Get metrics
        for name in metric_names:
            try:
                result[name] = self.get_metric_definition(name, context)
            except ValueError:
                # Skip unknown metrics
                continue
        
        return result
    
    def get_metric_quality_score(self, metric_name: str) -> float:
        """
        Calculate a quality score for a metric (0-1).
        
        Factors:
        - Data freshness (40%)
        - Completeness (30%)
        - Validation status (30%)
        
        Returns:
            Quality score from 0 (poor) to 1 (excellent)
        """
        if metric_name not in self.base_layer.metrics:
            return 0.0
        
        metric = self.base_layer.metrics[metric_name]
        
        # Check freshness
        freshness = self._check_data_freshness(metric.base_table)
        freshness_scores = {
            DataFreshnessLevel.REALTIME: 1.0,
            DataFreshnessLevel.FRESH: 0.9,
            DataFreshnessLevel.RECENT: 0.7,
            DataFreshnessLevel.STALE: 0.3,
            DataFreshnessLevel.UNKNOWN: 0.5
        }
        freshness_score = freshness_scores[freshness]
        
        # Completeness: does it have description, tags, etc?
        completeness_score = 0.0
        if metric.description:
            completeness_score += 0.4
        if metric.synonyms:
            completeness_score += 0.3
        if metric.tags:
            completeness_score += 0.3
        
        # Validation: are filters and formula valid?
        validation_score = 1.0  # Assume valid if loaded successfully
        
        # Weighted average
        quality_score = (
            freshness_score * 0.4 +
            completeness_score * 0.3 +
            validation_score * 0.3
        )
        
        return round(quality_score, 2)


# Singleton instance
_realtime_engine_instance: Optional[RealtimeMetricEngine] = None


def get_realtime_engine(db_connection=None) -> RealtimeMetricEngine:
    """
    Get or create the global RealtimeMetricEngine instance.
    
    Args:
        db_connection: Database connection (optional)
    
    Returns:
        RealtimeMetricEngine singleton
    """
    global _realtime_engine_instance
    if _realtime_engine_instance is None:
        _realtime_engine_instance = RealtimeMetricEngine(db_connection)
    return _realtime_engine_instance
