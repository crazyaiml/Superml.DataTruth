"""
Time intelligence module for DataTruth.

Provides time-based calculations including:
- Year-over-Year (YoY) growth
- Month-over-Month (MoM) growth
- Quarter-over-Quarter (QoQ) growth
- Compound Annual Growth Rate (CAGR)
- Period comparisons
- Trend analysis
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
import math


class TimeGrain(str, Enum):
    """Time granularity for aggregations."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class GrowthMetrics(BaseModel):
    """Growth calculation results."""
    current_value: float = Field(description="Current period value")
    previous_value: float = Field(description="Previous period value")
    absolute_change: float = Field(description="Absolute change (current - previous)")
    percent_change: float = Field(description="Percentage change")
    direction: str = Field(description="Growth direction: up, down, or flat")
    
    @property
    def is_growth(self) -> bool:
        """Check if this represents growth."""
        return self.absolute_change > 0
    
    @property
    def is_decline(self) -> bool:
        """Check if this represents decline."""
        return self.absolute_change < 0
    
    @property
    def is_flat(self) -> bool:
        """Check if there's no change."""
        return abs(self.absolute_change) < 0.01


class PeriodComparison(BaseModel):
    """Comparison between two time periods."""
    current_period: str = Field(description="Current period label")
    previous_period: str = Field(description="Previous period label")
    growth: GrowthMetrics = Field(description="Growth metrics")


class TrendAnalysis(BaseModel):
    """Trend analysis results."""
    data_points: List[Tuple[str, float]] = Field(description="Time series data points (period, value)")
    trend: str = Field(description="Overall trend: increasing, decreasing, stable, or volatile")
    avg_growth_rate: float = Field(description="Average growth rate across periods")
    volatility: float = Field(description="Volatility measure (std dev of changes)")
    best_period: Tuple[str, float] = Field(description="Period with highest value")
    worst_period: Tuple[str, float] = Field(description="Period with lowest value")


class TimeIntelligence:
    """
    Time intelligence calculations for analytics.
    
    Provides methods for calculating various time-based metrics including
    growth rates, period comparisons, and trend analysis.
    """
    
    def __init__(self):
        """Initialize time intelligence calculator."""
        pass
    
    def calculate_yoy_growth(
        self,
        current_value: float,
        previous_year_value: float
    ) -> GrowthMetrics:
        """
        Calculate Year-over-Year growth.
        
        Args:
            current_value: Value for current year
            previous_year_value: Value for previous year
        
        Returns:
            GrowthMetrics with YoY calculation
        """
        return self._calculate_growth(current_value, previous_year_value, "YoY")
    
    def calculate_mom_growth(
        self,
        current_value: float,
        previous_month_value: float
    ) -> GrowthMetrics:
        """
        Calculate Month-over-Month growth.
        
        Args:
            current_value: Value for current month
            previous_month_value: Value for previous month
        
        Returns:
            GrowthMetrics with MoM calculation
        """
        return self._calculate_growth(current_value, previous_month_value, "MoM")
    
    def calculate_qoq_growth(
        self,
        current_value: float,
        previous_quarter_value: float
    ) -> GrowthMetrics:
        """
        Calculate Quarter-over-Quarter growth.
        
        Args:
            current_value: Value for current quarter
            previous_quarter_value: Value for previous quarter
        
        Returns:
            GrowthMetrics with QoQ calculation
        """
        return self._calculate_growth(current_value, previous_quarter_value, "QoQ")
    
    def _calculate_growth(
        self,
        current: float,
        previous: float,
        label: str = ""
    ) -> GrowthMetrics:
        """
        Internal method to calculate growth metrics.
        
        Args:
            current: Current period value
            previous: Previous period value
            label: Optional label for the calculation
        
        Returns:
            GrowthMetrics object
        """
        absolute_change = current - previous
        
        # Handle division by zero
        if abs(previous) < 0.01:
            if abs(current) < 0.01:
                percent_change = 0.0
            else:
                # Previous was ~0, current is not - infinite growth
                percent_change = float('inf') if current > 0 else float('-inf')
        else:
            percent_change = (absolute_change / abs(previous)) * 100
        
        # Determine direction
        if abs(absolute_change) < 0.01:
            direction = "flat"
        elif absolute_change > 0:
            direction = "up"
        else:
            direction = "down"
        
        return GrowthMetrics(
            current_value=current,
            previous_value=previous,
            absolute_change=absolute_change,
            percent_change=percent_change,
            direction=direction
        )
    
    def calculate_cagr(
        self,
        start_value: float,
        end_value: float,
        num_years: float
    ) -> float:
        """
        Calculate Compound Annual Growth Rate.
        
        Formula: CAGR = (End Value / Start Value)^(1 / num_years) - 1
        
        Args:
            start_value: Starting value
            end_value: Ending value
            num_years: Number of years between start and end
        
        Returns:
            CAGR as a percentage
        
        Raises:
            ValueError: If start_value <= 0 or num_years <= 0
        """
        if start_value <= 0:
            raise ValueError("Start value must be positive for CAGR calculation")
        if num_years <= 0:
            raise ValueError("Number of years must be positive")
        
        if abs(end_value) < 0.01:
            # End value is ~0, complete decline
            return -100.0
        
        # CAGR = (End/Start)^(1/years) - 1
        ratio = end_value / start_value
        cagr = (math.pow(ratio, 1.0 / num_years) - 1) * 100
        
        return cagr
    
    def compare_periods(
        self,
        current_data: Dict[str, float],
        previous_data: Dict[str, float],
        period_label: str = "Period"
    ) -> List[PeriodComparison]:
        """
        Compare metrics between two time periods.
        
        Args:
            current_data: Dict of metric_name -> value for current period
            previous_data: Dict of metric_name -> value for previous period
            period_label: Label for the period type (e.g., "Month", "Quarter")
        
        Returns:
            List of PeriodComparison objects
        """
        comparisons = []
        
        # Get all metrics (union of both periods)
        all_metrics = set(current_data.keys()) | set(previous_data.keys())
        
        for metric in all_metrics:
            current_val = current_data.get(metric, 0.0)
            previous_val = previous_data.get(metric, 0.0)
            
            growth = self._calculate_growth(current_val, previous_val)
            
            comparisons.append(PeriodComparison(
                current_period=f"Current {period_label}",
                previous_period=f"Previous {period_label}",
                growth=growth
            ))
        
        return comparisons
    
    def analyze_trend(
        self,
        time_series: List[Tuple[str, float]],
        threshold: float = 0.1
    ) -> TrendAnalysis:
        """
        Analyze trend in time series data.
        
        Args:
            time_series: List of (period_label, value) tuples
            threshold: Threshold for determining stable trend (default 0.1 = 10%)
        
        Returns:
            TrendAnalysis object
        
        Raises:
            ValueError: If time_series has fewer than 2 data points
        """
        if len(time_series) < 2:
            raise ValueError("Time series must have at least 2 data points")
        
        # Extract values
        values = [val for _, val in time_series]
        
        # Calculate period-over-period changes
        changes = []
        growth_rates = []
        for i in range(1, len(values)):
            change = values[i] - values[i-1]
            changes.append(change)
            
            # Calculate growth rate
            if abs(values[i-1]) > 0.01:
                growth_rate = (change / abs(values[i-1])) * 100
                growth_rates.append(growth_rate)
        
        # Calculate average growth rate
        avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0.0
        
        # Calculate volatility (standard deviation of changes)
        if len(changes) > 1:
            mean_change = sum(changes) / len(changes)
            variance = sum((c - mean_change) ** 2 for c in changes) / len(changes)
            volatility = math.sqrt(variance)
        else:
            volatility = 0.0
        
        # Determine trend
        if volatility / (abs(sum(values) / len(values)) + 0.01) > threshold:
            trend = "volatile"
        elif abs(avg_growth_rate) < threshold:
            trend = "stable"
        elif avg_growth_rate > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Find best and worst periods
        best_idx = max(range(len(values)), key=lambda i: values[i])
        worst_idx = min(range(len(values)), key=lambda i: values[i])
        
        return TrendAnalysis(
            data_points=time_series,
            trend=trend,
            avg_growth_rate=avg_growth_rate,
            volatility=volatility,
            best_period=time_series[best_idx],
            worst_period=time_series[worst_idx]
        )
    
    def calculate_period_totals(
        self,
        data: List[Dict[str, Any]],
        date_field: str,
        value_field: str,
        grain: TimeGrain
    ) -> Dict[str, float]:
        """
        Aggregate data by time period.
        
        Args:
            data: List of data records
            date_field: Name of the date field
            value_field: Name of the value field to aggregate
            grain: Time granularity for aggregation
        
        Returns:
            Dict mapping period label to total value
        """
        period_totals: Dict[str, float] = {}
        
        for record in data:
            date_val = record.get(date_field)
            value = record.get(value_field, 0.0)
            
            if not date_val:
                continue
            
            # Parse date if it's a string
            if isinstance(date_val, str):
                try:
                    date_val = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                except ValueError:
                    continue
            
            # Get period label based on grain
            if grain == TimeGrain.DAY:
                period = date_val.strftime("%Y-%m-%d")
            elif grain == TimeGrain.WEEK:
                # ISO week number
                period = f"{date_val.year}-W{date_val.isocalendar()[1]:02d}"
            elif grain == TimeGrain.MONTH:
                period = date_val.strftime("%Y-%m")
            elif grain == TimeGrain.QUARTER:
                quarter = (date_val.month - 1) // 3 + 1
                period = f"{date_val.year}-Q{quarter}"
            else:  # YEAR
                period = str(date_val.year)
            
            period_totals[period] = period_totals.get(period, 0.0) + value
        
        return period_totals


# Global singleton instance
_time_intelligence_instance: Optional[TimeIntelligence] = None


def get_time_intelligence() -> TimeIntelligence:
    """
    Get the global TimeIntelligence instance.
    
    Returns:
        TimeIntelligence singleton
    """
    global _time_intelligence_instance
    if _time_intelligence_instance is None:
        _time_intelligence_instance = TimeIntelligence()
    return _time_intelligence_instance


# Convenience functions
def calculate_yoy_growth(current: float, previous: float) -> GrowthMetrics:
    """Calculate Year-over-Year growth."""
    return get_time_intelligence().calculate_yoy_growth(current, previous)


def calculate_mom_growth(current: float, previous: float) -> GrowthMetrics:
    """Calculate Month-over-Month growth."""
    return get_time_intelligence().calculate_mom_growth(current, previous)


def calculate_cagr(start: float, end: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate."""
    return get_time_intelligence().calculate_cagr(start, end, years)
