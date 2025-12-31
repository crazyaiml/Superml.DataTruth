"""
Attribution Analysis Module

Analyzes what factors drive or influence key metrics.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import math


class AttributionFactor(BaseModel):
    """Factor contributing to a metric."""
    factor_name: str = Field(description="Name of the factor")
    correlation: float = Field(description="Correlation coefficient (-1 to 1)")
    importance: float = Field(description="Relative importance (0-1)")
    direction: str = Field(description="positive, negative, or neutral")
    confidence: float = Field(description="Statistical confidence (0-1)")


class AttributionResult(BaseModel):
    """Attribution analysis result."""
    target_metric: str = Field(description="Metric being explained")
    factors: List[AttributionFactor] = Field(description="Contributing factors")
    explained_variance: float = Field(description="How much variance is explained (0-1)")
    top_driver: Optional[str] = Field(None, description="Most important factor")


class AttributionAnalyzer:
    """Analyzes what drives metrics using correlation and importance."""
    
    def analyze_drivers(
        self,
        target_values: List[float],
        factor_values: Dict[str, List[float]],
        target_name: str = "metric"
    ) -> AttributionResult:
        """
        Analyze what factors drive a target metric.
        
        Args:
            target_values: Values of the target metric
            factor_values: Dict of factor_name -> values
            target_name: Name of the target metric
            
        Returns:
            AttributionResult with driver analysis
        """
        if len(target_values) < 3:
            raise ValueError("Need at least 3 data points for attribution")
        
        factors = []
        
        for factor_name, values in factor_values.items():
            if len(values) != len(target_values):
                continue  # Skip mismatched lengths
            
            # Calculate correlation
            correlation = self._calculate_correlation(target_values, values)
            
            # Calculate importance (normalized absolute correlation)
            importance = abs(correlation)
            
            # Determine direction
            if correlation > 0.3:
                direction = "positive"
            elif correlation < -0.3:
                direction = "negative"
            else:
                direction = "neutral"
            
            # Confidence based on sample size and correlation strength
            n = len(values)
            confidence = min(1.0, (abs(correlation) * math.sqrt(n)) / 3.0)
            
            factors.append(AttributionFactor(
                factor_name=factor_name,
                correlation=correlation,
                importance=importance,
                direction=direction,
                confidence=confidence
            ))
        
        # Sort by importance
        factors.sort(key=lambda x: x.importance, reverse=True)
        
        # Calculate explained variance (simplified)
        if factors:
            # Sum of squared correlations (rough approximation)
            explained_variance = min(1.0, sum(f.correlation ** 2 for f in factors[:3]))
            top_driver = factors[0].factor_name if factors else None
        else:
            explained_variance = 0.0
            top_driver = None
        
        return AttributionResult(
            target_metric=target_name,
            factors=factors,
            explained_variance=explained_variance,
            top_driver=top_driver
        )
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n == 0:
            return 0.0
        
        # Calculate means
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        # Calculate covariance and standard deviations
        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        
        # Correlation
        if std_x == 0 or std_y == 0:
            return 0.0
        
        correlation = cov / (std_x * std_y)
        return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]


def get_attribution_analyzer() -> AttributionAnalyzer:
    """Get AttributionAnalyzer instance."""
    return AttributionAnalyzer()
