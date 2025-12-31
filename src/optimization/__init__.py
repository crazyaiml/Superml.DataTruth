"""
Query Optimization Module

Provides query optimization features including pagination, query plan caching,
performance analysis, and EXPLAIN plan analysis.
"""

from src.optimization.pagination import PaginationParams, paginate_results, get_pagination_metadata
from src.optimization.plan_cache import QueryPlanCache, get_plan_cache
from src.optimization.analyzer import QueryAnalyzer, PerformanceMetrics, get_query_analyzer
from src.optimization.explainer import ExplainAnalyzer, ExplainPlan, get_explain_analyzer

__all__ = [
    "PaginationParams",
    "paginate_results",
    "get_pagination_metadata",
    "QueryPlanCache",
    "get_plan_cache",
    "QueryAnalyzer",
    "PerformanceMetrics",
    "get_query_analyzer",
    "ExplainAnalyzer",
    "ExplainPlan",
    "get_explain_analyzer",
]
