"""
Advanced analytics module for DataTruth.

Provides time intelligence, statistical analysis, and anomaly detection
capabilities for query results.
"""

from .time_intelligence import (
    TimeIntelligence,
    TimeGrain,
    GrowthMetrics,
    calculate_yoy_growth,
    calculate_mom_growth,
    calculate_cagr,
    get_time_intelligence
)

from .statistics import (
    StatisticalAnalyzer,
    DescriptiveStats,
    DistributionStats,
    calculate_descriptive_stats,
    calculate_distribution,
    get_statistical_analyzer
)

from .anomaly import (
    AnomalyDetector,
    AnomalyResult,
    AnomalyMethod,
    detect_anomalies,
    get_anomaly_detector
)

__all__ = [
    # Time Intelligence
    "TimeIntelligence",
    "TimeGrain",
    "GrowthMetrics",
    "calculate_yoy_growth",
    "calculate_mom_growth",
    "calculate_cagr",
    "get_time_intelligence",
    
    # Statistics
    "StatisticalAnalyzer",
    "DescriptiveStats",
    "DistributionStats",
    "calculate_descriptive_stats",
    "calculate_distribution",
    "get_statistical_analyzer",
    
    # Anomaly Detection
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalyMethod",
    "detect_anomalies",
    "get_anomaly_detector",
]
