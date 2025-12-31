"""
Forecasting Module

Time series forecasting for augmented insights using statistical methods.
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
import math


class ForecastMethod(str, Enum):
    """Forecasting methods."""
    LINEAR = "linear"  # Simple linear regression
    MOVING_AVERAGE = "moving_average"  # Moving average
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"  # Exponential smoothing


class ForecastPoint(BaseModel):
    """Single forecast point."""
    timestamp: str = Field(description="Timestamp of forecast")
    value: float = Field(description="Forecasted value")
    lower_bound: Optional[float] = Field(None, description="Lower confidence bound")
    upper_bound: Optional[float] = Field(None, description="Upper confidence bound")
    confidence: float = Field(description="Confidence in forecast (0-1)")


class ForecastResult(BaseModel):
    """Forecast result."""
    method: ForecastMethod = Field(description="Method used")
    forecasts: List[ForecastPoint] = Field(description="Forecast points")
    accuracy_score: Optional[float] = Field(None, description="Historical accuracy if available")
    trend_direction: str = Field(description="up, down, or stable")
    trend_strength: float = Field(description="Strength of trend (0-1)")


class Forecaster:
    """Time series forecasting using statistical methods."""
    
    def forecast(
        self,
        values: List[float],
        periods: int = 7,
        method: ForecastMethod = ForecastMethod.LINEAR
    ) -> ForecastResult:
        """
        Forecast future values based on historical data.
        
        Args:
            values: Historical values
            periods: Number of periods to forecast
            method: Forecasting method to use
            
        Returns:
            ForecastResult with predictions
        """
        if len(values) < 3:
            raise ValueError("Need at least 3 historical values for forecasting")
        
        if method == ForecastMethod.LINEAR:
            return self._linear_forecast(values, periods)
        elif method == ForecastMethod.MOVING_AVERAGE:
            return self._moving_average_forecast(values, periods)
        elif method == ForecastMethod.EXPONENTIAL_SMOOTHING:
            return self._exponential_smoothing_forecast(values, periods)
        else:
            raise ValueError(f"Unknown forecast method: {method}")
    
    def _linear_forecast(self, values: List[float], periods: int) -> ForecastResult:
        """Simple linear regression forecast."""
        n = len(values)
        
        # Calculate linear regression: y = mx + b
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * v for i, v in enumerate(values))
        sum_x2 = sum(i * i for i in range(n))
        
        # Slope
        m = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Intercept
        b = (sum_y - m * sum_x) / n
        
        # Determine trend
        trend_direction = "up" if m > 0.1 else ("down" if m < -0.1 else "stable")
        trend_strength = min(abs(m) / (sum_y / n) if sum_y != 0 else 0, 1.0)
        
        # Calculate standard error for confidence bounds
        residuals = [values[i] - (m * i + b) for i in range(n)]
        se = math.sqrt(sum(r * r for r in residuals) / (n - 2))
        
        # Generate forecasts
        forecasts = []
        for i in range(periods):
            x = n + i
            predicted = m * x + b
            
            # Confidence bounds (simple approximation)
            margin = 1.96 * se * math.sqrt(1 + 1/n + (x - sum_x/n)**2 / sum_x2)
            
            forecasts.append(ForecastPoint(
                timestamp=f"T+{i+1}",
                value=predicted,
                lower_bound=predicted - margin,
                upper_bound=predicted + margin,
                confidence=max(0.5, 1.0 - (i * 0.05))  # Decreasing confidence
            ))
        
        return ForecastResult(
            method=ForecastMethod.LINEAR,
            forecasts=forecasts,
            trend_direction=trend_direction,
            trend_strength=trend_strength
        )
    
    def _moving_average_forecast(self, values: List[float], periods: int, window: int = 3) -> ForecastResult:
        """Moving average forecast."""
        if len(values) < window:
            window = len(values)
        
        # Calculate moving average
        last_ma = sum(values[-window:]) / window
        
        # Simple trend detection
        if len(values) >= window * 2:
            earlier_ma = sum(values[-window*2:-window]) / window
            trend = last_ma - earlier_ma
        else:
            trend = 0
        
        trend_direction = "up" if trend > 0.1 else ("down" if trend < -0.1 else "stable")
        avg_value = sum(values) / len(values)
        trend_strength = min(abs(trend) / avg_value if avg_value != 0 else 0, 1.0)
        
        # Calculate standard deviation for confidence
        std_dev = math.sqrt(sum((v - avg_value) ** 2 for v in values) / len(values))
        
        forecasts = []
        current = last_ma
        for i in range(periods):
            current += trend
            margin = 1.96 * std_dev
            
            forecasts.append(ForecastPoint(
                timestamp=f"T+{i+1}",
                value=current,
                lower_bound=current - margin,
                upper_bound=current + margin,
                confidence=max(0.5, 1.0 - (i * 0.08))
            ))
        
        return ForecastResult(
            method=ForecastMethod.MOVING_AVERAGE,
            forecasts=forecasts,
            trend_direction=trend_direction,
            trend_strength=trend_strength
        )
    
    def _exponential_smoothing_forecast(self, values: List[float], periods: int, alpha: float = 0.3) -> ForecastResult:
        """Exponential smoothing forecast."""
        if not 0 < alpha < 1:
            alpha = 0.3
        
        # Calculate smoothed values
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
        
        # Estimate trend
        if len(smoothed) >= 2:
            trend = smoothed[-1] - smoothed[-2]
        else:
            trend = 0
        
        trend_direction = "up" if trend > 0.1 else ("down" if trend < -0.1 else "stable")
        avg_value = sum(values) / len(values)
        trend_strength = min(abs(trend) / avg_value if avg_value != 0 else 0, 1.0)
        
        # Calculate prediction error
        errors = [values[i] - smoothed[i] for i in range(len(values))]
        mse = sum(e * e for e in errors) / len(errors)
        std_error = math.sqrt(mse)
        
        forecasts = []
        last_smooth = smoothed[-1]
        for i in range(periods):
            predicted = last_smooth + trend * (i + 1)
            margin = 1.96 * std_error * math.sqrt(i + 1)
            
            forecasts.append(ForecastPoint(
                timestamp=f"T+{i+1}",
                value=predicted,
                lower_bound=predicted - margin,
                upper_bound=predicted + margin,
                confidence=max(0.5, 1.0 - (i * 0.06))
            ))
        
        return ForecastResult(
            method=ForecastMethod.EXPONENTIAL_SMOOTHING,
            forecasts=forecasts,
            trend_direction=trend_direction,
            trend_strength=trend_strength
        )


def get_forecaster() -> Forecaster:
    """Get Forecaster instance."""
    return Forecaster()
