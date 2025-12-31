"""
Query Performance Analyzer

Tracks query execution metrics and provides performance analysis.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Query performance metrics."""
    
    query_hash: str = Field(description="Hash of the SQL query")
    execution_count: int = Field(default=0, description="Number of times executed")
    total_time_ms: float = Field(default=0.0, description="Total execution time in ms")
    avg_time_ms: float = Field(default=0.0, description="Average execution time in ms")
    min_time_ms: float = Field(default=float('inf'), description="Minimum execution time in ms")
    max_time_ms: float = Field(default=0.0, description="Maximum execution time in ms")
    total_rows: int = Field(default=0, description="Total rows returned")
    avg_rows: float = Field(default=0.0, description="Average rows per execution")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate percentage")
    last_executed: Optional[str] = Field(default=None, description="Last execution timestamp")
    slow_query_threshold_ms: float = Field(default=1000.0, description="Threshold for slow queries")
    is_slow: bool = Field(default=False, description="Whether query is considered slow")


class QueryAnalyzer:
    """Analyzes and tracks query performance metrics."""
    
    def __init__(self, slow_query_threshold_ms: float = 1000.0):
        """
        Initialize query analyzer.
        
        Args:
            slow_query_threshold_ms: Threshold for considering queries slow
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.slow_queries: List[Dict[str, Any]] = []
    
    def record_execution(
        self,
        query_hash: str,
        execution_time_ms: float,
        row_count: int,
        from_cache: bool = False
    ):
        """
        Record a query execution.
        
        Args:
            query_hash: Hash of the SQL query
            execution_time_ms: Execution time in milliseconds
            row_count: Number of rows returned
            from_cache: Whether result came from cache
        """
        if query_hash not in self.metrics:
            self.metrics[query_hash] = PerformanceMetrics(
                query_hash=query_hash,
                slow_query_threshold_ms=self.slow_query_threshold_ms
            )
        
        metric = self.metrics[query_hash]
        
        # Update counts
        metric.execution_count += 1
        metric.total_rows += row_count
        
        # Update cache stats
        if from_cache:
            metric.cache_hits += 1
        else:
            metric.cache_misses += 1
        
        # Update timing stats
        metric.total_time_ms += execution_time_ms
        metric.avg_time_ms = metric.total_time_ms / metric.execution_count
        metric.min_time_ms = min(metric.min_time_ms, execution_time_ms)
        metric.max_time_ms = max(metric.max_time_ms, execution_time_ms)
        
        # Update average rows
        metric.avg_rows = metric.total_rows / metric.execution_count
        
        # Update cache hit rate
        total_requests = metric.cache_hits + metric.cache_misses
        metric.cache_hit_rate = (metric.cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        # Update last executed timestamp
        metric.last_executed = datetime.now().isoformat()
        
        # Check if slow query
        metric.is_slow = execution_time_ms > self.slow_query_threshold_ms
        
        # Track slow queries
        if metric.is_slow and not from_cache:
            self.slow_queries.append({
                "query_hash": query_hash,
                "execution_time_ms": execution_time_ms,
                "row_count": row_count,
                "timestamp": metric.last_executed
            })
    
    def get_metrics(self, query_hash: str) -> Optional[PerformanceMetrics]:
        """
        Get metrics for a specific query.
        
        Args:
            query_hash: Hash of the SQL query
            
        Returns:
            Performance metrics or None if not found
        """
        return self.metrics.get(query_hash)
    
    def get_all_metrics(self) -> List[PerformanceMetrics]:
        """
        Get metrics for all queries.
        
        Returns:
            List of performance metrics
        """
        return list(self.metrics.values())
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent slow queries.
        
        Args:
            limit: Maximum number of slow queries to return
            
        Returns:
            List of slow query details
        """
        # Sort by execution time (slowest first)
        sorted_slow = sorted(
            self.slow_queries,
            key=lambda x: x['execution_time_ms'],
            reverse=True
        )
        
        return sorted_slow[:limit]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary.
        
        Returns:
            Summary statistics
        """
        if not self.metrics:
            return {
                "total_queries": 0,
                "total_executions": 0,
                "avg_execution_time_ms": 0.0,
                "cache_hit_rate": 0.0,
                "slow_query_count": 0
            }
        
        total_executions = sum(m.execution_count for m in self.metrics.values())
        total_time = sum(m.total_time_ms for m in self.metrics.values())
        total_cache_hits = sum(m.cache_hits for m in self.metrics.values())
        total_cache_misses = sum(m.cache_misses for m in self.metrics.values())
        slow_count = sum(1 for m in self.metrics.values() if m.is_slow)
        
        total_requests = total_cache_hits + total_cache_misses
        cache_hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "total_queries": len(self.metrics),
            "total_executions": total_executions,
            "avg_execution_time_ms": total_time / total_executions if total_executions > 0 else 0.0,
            "cache_hit_rate": cache_hit_rate,
            "slow_query_count": slow_count,
            "slowest_query_ms": max((m.max_time_ms for m in self.metrics.values()), default=0.0),
            "fastest_query_ms": min((m.min_time_ms for m in self.metrics.values()), default=0.0)
        }
    
    def get_top_queries(self, by: str = "execution_count", limit: int = 10) -> List[PerformanceMetrics]:
        """
        Get top queries by a specific metric.
        
        Args:
            by: Metric to sort by (execution_count, avg_time_ms, total_time_ms)
            limit: Number of queries to return
            
        Returns:
            List of top queries
        """
        if by not in ["execution_count", "avg_time_ms", "total_time_ms", "max_time_ms"]:
            by = "execution_count"
        
        sorted_metrics = sorted(
            self.metrics.values(),
            key=lambda m: getattr(m, by),
            reverse=True
        )
        
        return sorted_metrics[:limit]
    
    def reset_metrics(self, query_hash: Optional[str] = None):
        """
        Reset metrics for a specific query or all queries.
        
        Args:
            query_hash: Hash of query to reset, or None to reset all
        """
        if query_hash:
            if query_hash in self.metrics:
                del self.metrics[query_hash]
        else:
            self.metrics.clear()
            self.slow_queries.clear()
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics for persistence or analysis.
        
        Returns:
            Dictionary with all metrics and slow queries
        """
        return {
            "metrics": {k: v.model_dump() for k, v in self.metrics.items()},
            "slow_queries": self.slow_queries,
            "summary": self.get_summary(),
            "exported_at": datetime.now().isoformat()
        }


# Singleton instance
_query_analyzer_instance = None


def get_query_analyzer() -> QueryAnalyzer:
    """
    Get or create the global QueryAnalyzer instance.
    
    Returns:
        QueryAnalyzer singleton
    """
    global _query_analyzer_instance
    
    if _query_analyzer_instance is None:
        _query_analyzer_instance = QueryAnalyzer()
    
    return _query_analyzer_instance
