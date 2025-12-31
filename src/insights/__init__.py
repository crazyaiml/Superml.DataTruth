"""
Insights Module

Automated insight generation for database connections and query patterns.
"""

from src.insights.models import (
    InsightType,
    InsightSeverity,
    Insight,
    InsightCard,
    InsightsResponse
)
from src.insights.generator import InsightGenerator, get_insight_generator

__all__ = [
    'InsightType',
    'InsightSeverity',
    'Insight',
    'InsightCard',
    'InsightsResponse',
    'InsightGenerator',
    'get_insight_generator'
]
