"""
Statistical analysis module for DataTruth.

Provides descriptive statistics, distribution analysis, and correlation
calculations for query results.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import math
from collections import Counter


class DescriptiveStats(BaseModel):
    """Descriptive statistics for a dataset."""
    count: int = Field(description="Number of data points")
    sum: float = Field(description="Sum of all values")
    mean: float = Field(description="Arithmetic mean")
    median: float = Field(description="Median value")
    mode: Optional[float] = Field(description="Most frequent value")
    std_dev: float = Field(description="Standard deviation")
    variance: float = Field(description="Variance")
    min: float = Field(description="Minimum value")
    max: float = Field(description="Maximum value")
    range: float = Field(description="Range (max - min)")
    q1: float = Field(description="First quartile (25th percentile)")
    q3: float = Field(description="Third quartile (75th percentile)")
    iqr: float = Field(description="Interquartile range (Q3 - Q1)")


class DistributionStats(BaseModel):
    """Distribution analysis results."""
    skewness: float = Field(description="Skewness (asymmetry measure)")
    kurtosis: float = Field(description="Kurtosis (tailedness measure)")
    is_normal: bool = Field(description="Rough normality check")
    outlier_count: int = Field(description="Number of outliers detected")
    outliers: List[float] = Field(description="Outlier values")


class CorrelationResult(BaseModel):
    """Correlation analysis result."""
    variable_x: str = Field(description="First variable name")
    variable_y: str = Field(description="Second variable name")
    correlation: float = Field(description="Correlation coefficient (-1 to 1)")
    strength: str = Field(description="Correlation strength: weak, moderate, strong")
    direction: str = Field(description="Correlation direction: positive, negative, none")


class StatisticalAnalyzer:
    """
    Statistical analysis for query results.
    
    Provides methods for calculating descriptive statistics, distribution
    analysis, and correlation metrics.
    """
    
    def __init__(self):
        """Initialize statistical analyzer."""
        pass
    
    def calculate_descriptive_stats(
        self,
        data: List[float],
        calculate_mode: bool = True
    ) -> DescriptiveStats:
        """
        Calculate descriptive statistics for a dataset.
        
        Args:
            data: List of numeric values
            calculate_mode: Whether to calculate mode (can be slow for large datasets)
        
        Returns:
            DescriptiveStats object
        
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Cannot calculate statistics for empty dataset")
        
        n = len(data)
        sorted_data = sorted(data)
        
        # Basic stats
        total = sum(data)
        mean = total / n
        min_val = sorted_data[0]
        max_val = sorted_data[-1]
        data_range = max_val - min_val
        
        # Median
        if n % 2 == 0:
            median = (sorted_data[n//2 - 1] + sorted_data[n//2]) / 2
        else:
            median = sorted_data[n//2]
        
        # Mode (most frequent value)
        mode = None
        if calculate_mode:
            # Round to 2 decimals to group similar values
            rounded_data = [round(x, 2) for x in data]
            counter = Counter(rounded_data)
            most_common = counter.most_common(1)
            if most_common and most_common[0][1] > 1:  # Only if appears more than once
                mode = float(most_common[0][0])
        
        # Variance and standard deviation
        variance = sum((x - mean) ** 2 for x in data) / n
        std_dev = math.sqrt(variance)
        
        # Quartiles
        q1_index = n // 4
        q3_index = 3 * n // 4
        q1 = sorted_data[q1_index]
        q3 = sorted_data[q3_index]
        iqr = q3 - q1
        
        return DescriptiveStats(
            count=n,
            sum=total,
            mean=mean,
            median=median,
            mode=mode,
            std_dev=std_dev,
            variance=variance,
            min=min_val,
            max=max_val,
            range=data_range,
            q1=q1,
            q3=q3,
            iqr=iqr
        )
    
    def calculate_distribution(
        self,
        data: List[float],
        descriptive_stats: Optional[DescriptiveStats] = None
    ) -> DistributionStats:
        """
        Analyze distribution characteristics.
        
        Args:
            data: List of numeric values
            descriptive_stats: Pre-calculated descriptive stats (optional)
        
        Returns:
            DistributionStats object
        
        Raises:
            ValueError: If data has fewer than 3 points
        """
        if len(data) < 3:
            raise ValueError("Need at least 3 data points for distribution analysis")
        
        # Calculate descriptive stats if not provided
        if descriptive_stats is None:
            descriptive_stats = self.calculate_descriptive_stats(data, calculate_mode=False)
        
        n = descriptive_stats.count
        mean = descriptive_stats.mean
        std_dev = descriptive_stats.std_dev
        
        # Skewness (Fisher-Pearson coefficient)
        if std_dev > 0:
            skewness = sum(((x - mean) / std_dev) ** 3 for x in data) / n
        else:
            skewness = 0.0
        
        # Kurtosis (excess kurtosis, normal distribution = 0)
        if std_dev > 0:
            kurtosis = (sum(((x - mean) / std_dev) ** 4 for x in data) / n) - 3
        else:
            kurtosis = 0.0
        
        # Rough normality check
        # Normal distribution: skewness ≈ 0, kurtosis ≈ 0
        is_normal = abs(skewness) < 1.0 and abs(kurtosis) < 1.0
        
        # Outlier detection using IQR method
        lower_bound = descriptive_stats.q1 - 1.5 * descriptive_stats.iqr
        upper_bound = descriptive_stats.q3 + 1.5 * descriptive_stats.iqr
        
        outliers = [x for x in data if x < lower_bound or x > upper_bound]
        
        return DistributionStats(
            skewness=skewness,
            kurtosis=kurtosis,
            is_normal=is_normal,
            outlier_count=len(outliers),
            outliers=sorted(outliers)
        )
    
    def calculate_correlation(
        self,
        x: List[float],
        y: List[float],
        x_name: str = "X",
        y_name: str = "Y"
    ) -> CorrelationResult:
        """
        Calculate Pearson correlation coefficient between two variables.
        
        Args:
            x: First variable data
            y: Second variable data
            x_name: Name of first variable
            y_name: Name of second variable
        
        Returns:
            CorrelationResult object
        
        Raises:
            ValueError: If x and y have different lengths or fewer than 2 points
        """
        if len(x) != len(y):
            raise ValueError("Variables must have the same length")
        if len(x) < 2:
            raise ValueError("Need at least 2 data points for correlation")
        
        n = len(x)
        
        # Calculate means
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        # Calculate covariance and standard deviations
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        
        # Pearson correlation coefficient
        if std_x > 0 and std_y > 0:
            correlation = covariance / (std_x * std_y)
        else:
            correlation = 0.0
        
        # Determine strength and direction
        abs_corr = abs(correlation)
        if abs_corr < 0.3:
            strength = "weak"
        elif abs_corr < 0.7:
            strength = "moderate"
        else:
            strength = "strong"
        
        if abs(correlation) < 0.1:
            direction = "none"
        elif correlation > 0:
            direction = "positive"
        else:
            direction = "negative"
        
        return CorrelationResult(
            variable_x=x_name,
            variable_y=y_name,
            correlation=correlation,
            strength=strength,
            direction=direction
        )
    
    def calculate_percentile(self, data: List[float], percentile: float) -> float:
        """
        Calculate a specific percentile.
        
        Args:
            data: List of numeric values
            percentile: Percentile to calculate (0-100)
        
        Returns:
            Value at the specified percentile
        
        Raises:
            ValueError: If data is empty or percentile is out of range
        """
        if not data:
            raise ValueError("Cannot calculate percentile for empty dataset")
        if not 0 <= percentile <= 100:
            raise ValueError("Percentile must be between 0 and 100")
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        # Linear interpolation method
        position = (percentile / 100) * (n - 1)
        lower_index = int(math.floor(position))
        upper_index = int(math.ceil(position))
        
        if lower_index == upper_index:
            return sorted_data[lower_index]
        
        # Interpolate
        weight = position - lower_index
        return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
    
    def calculate_z_scores(
        self,
        data: List[float],
        descriptive_stats: Optional[DescriptiveStats] = None
    ) -> List[float]:
        """
        Calculate z-scores (standard scores) for each data point.
        
        Z-score = (value - mean) / std_dev
        
        Args:
            data: List of numeric values
            descriptive_stats: Pre-calculated descriptive stats (optional)
        
        Returns:
            List of z-scores
        
        Raises:
            ValueError: If data is empty or has zero standard deviation
        """
        if not data:
            raise ValueError("Cannot calculate z-scores for empty dataset")
        
        if descriptive_stats is None:
            descriptive_stats = self.calculate_descriptive_stats(data, calculate_mode=False)
        
        if descriptive_stats.std_dev == 0:
            raise ValueError("Cannot calculate z-scores when standard deviation is zero")
        
        mean = descriptive_stats.mean
        std_dev = descriptive_stats.std_dev
        
        return [(x - mean) / std_dev for x in data]
    
    def identify_extremes(
        self,
        data: List[float],
        z_threshold: float = 3.0
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        Identify extreme values using z-score method.
        
        Args:
            data: List of numeric values
            z_threshold: Z-score threshold for extremes (default 3.0)
        
        Returns:
            Dict with 'high_extremes' and 'low_extremes' lists of (index, value) tuples
        """
        if not data:
            return {"high_extremes": [], "low_extremes": []}
        
        try:
            z_scores = self.calculate_z_scores(data)
        except ValueError:
            # Zero std dev or other issue
            return {"high_extremes": [], "low_extremes": []}
        
        high_extremes = []
        low_extremes = []
        
        for i, (value, z_score) in enumerate(zip(data, z_scores)):
            if z_score > z_threshold:
                high_extremes.append((i, value))
            elif z_score < -z_threshold:
                low_extremes.append((i, value))
        
        return {
            "high_extremes": high_extremes,
            "low_extremes": low_extremes
        }


# Global singleton instance
_statistical_analyzer_instance: Optional[StatisticalAnalyzer] = None


def get_statistical_analyzer() -> StatisticalAnalyzer:
    """
    Get the global StatisticalAnalyzer instance.
    
    Returns:
        StatisticalAnalyzer singleton
    """
    global _statistical_analyzer_instance
    if _statistical_analyzer_instance is None:
        _statistical_analyzer_instance = StatisticalAnalyzer()
    return _statistical_analyzer_instance


# Convenience functions
def calculate_descriptive_stats(data: List[float]) -> DescriptiveStats:
    """Calculate descriptive statistics for a dataset."""
    return get_statistical_analyzer().calculate_descriptive_stats(data)


def calculate_distribution(data: List[float]) -> DistributionStats:
    """Analyze distribution characteristics."""
    return get_statistical_analyzer().calculate_distribution(data)
