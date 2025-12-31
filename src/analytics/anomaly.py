"""
Anomaly detection module for DataTruth.

Provides various methods for detecting anomalies in query results including:
- Z-score method (statistical)
- IQR method (robust to outliers)
- Moving average method (time series)
- Threshold-based detection
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import math


class AnomalyMethod(str, Enum):
    """Anomaly detection methods."""
    Z_SCORE = "z_score"  # Statistical method using standard deviations
    IQR = "iqr"  # Interquartile range method
    MOVING_AVERAGE = "moving_average"  # Time series method
    THRESHOLD = "threshold"  # Simple threshold-based


class AnomalyType(str, Enum):
    """Type of anomaly detected."""
    HIGH = "high"  # Unusually high value
    LOW = "low"  # Unusually low value
    SPIKE = "spike"  # Sudden increase
    DROP = "drop"  # Sudden decrease


class Anomaly(BaseModel):
    """Single anomaly detection result."""
    index: int = Field(description="Index of anomalous data point")
    value: float = Field(description="Anomalous value")
    expected_value: Optional[float] = Field(description="Expected value (if applicable)")
    deviation: float = Field(description="Deviation from normal")
    severity: float = Field(description="Severity score (0-1, higher is more severe)")
    anomaly_type: AnomalyType = Field(description="Type of anomaly")
    confidence: float = Field(description="Confidence in detection (0-1)")


class AnomalyResult(BaseModel):
    """Anomaly detection results."""
    method: AnomalyMethod = Field(description="Detection method used")
    anomalies: List[Anomaly] = Field(description="Detected anomalies")
    total_points: int = Field(description="Total data points analyzed")
    anomaly_rate: float = Field(description="Percentage of anomalous points")
    summary: str = Field(description="Human-readable summary")
    
    @property
    def has_anomalies(self) -> bool:
        """Check if any anomalies were detected."""
        return len(self.anomalies) > 0
    
    @property
    def high_severity_count(self) -> int:
        """Count of high-severity anomalies (severity > 0.7)."""
        return sum(1 for a in self.anomalies if a.severity > 0.7)


class AnomalyDetector:
    """
    Anomaly detection for query results.
    
    Provides multiple methods for detecting anomalous data points including
    statistical, robust, and time-series based approaches.
    """
    
    def __init__(
        self,
        default_method: AnomalyMethod = AnomalyMethod.Z_SCORE,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5
    ):
        """
        Initialize anomaly detector.
        
        Args:
            default_method: Default detection method
            z_threshold: Z-score threshold for z_score method
            iqr_multiplier: IQR multiplier for iqr method
        """
        self.default_method = default_method
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
    
    def detect_anomalies(
        self,
        data: List[float],
        method: Optional[AnomalyMethod] = None,
        **kwargs
    ) -> AnomalyResult:
        """
        Detect anomalies in data using specified method.
        
        Args:
            data: List of numeric values
            method: Detection method (uses default if not specified)
            **kwargs: Method-specific parameters
        
        Returns:
            AnomalyResult object
        
        Raises:
            ValueError: If data is empty or invalid
        """
        if not data:
            raise ValueError("Cannot detect anomalies in empty dataset")
        
        method = method or self.default_method
        
        if method == AnomalyMethod.Z_SCORE:
            return self._detect_z_score(data, **kwargs)
        elif method == AnomalyMethod.IQR:
            return self._detect_iqr(data, **kwargs)
        elif method == AnomalyMethod.MOVING_AVERAGE:
            return self._detect_moving_average(data, **kwargs)
        elif method == AnomalyMethod.THRESHOLD:
            return self._detect_threshold(data, **kwargs)
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")
    
    def _detect_z_score(
        self,
        data: List[float],
        threshold: Optional[float] = None
    ) -> AnomalyResult:
        """
        Detect anomalies using z-score method.
        
        Points with |z-score| > threshold are considered anomalies.
        
        Args:
            data: List of numeric values
            threshold: Z-score threshold (uses default if not specified)
        
        Returns:
            AnomalyResult object
        """
        threshold = threshold or self.z_threshold
        n = len(data)
        
        # Calculate mean and standard deviation
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            # No variation - no anomalies
            return AnomalyResult(
                method=AnomalyMethod.Z_SCORE,
                anomalies=[],
                total_points=n,
                anomaly_rate=0.0,
                summary="No anomalies detected (zero variance)"
            )
        
        # Calculate z-scores and identify anomalies
        anomalies = []
        for i, value in enumerate(data):
            z_score = (value - mean) / std_dev
            abs_z = abs(z_score)
            
            if abs_z > threshold:
                # Determine anomaly type
                if z_score > 0:
                    anomaly_type = AnomalyType.HIGH
                else:
                    anomaly_type = AnomalyType.LOW
                
                # Calculate severity (normalized to 0-1)
                # Severity increases with z-score, caps at ~1.0 for z > 5
                severity = min(abs_z / 5.0, 1.0)
                
                # Confidence increases with distance from threshold
                confidence = min((abs_z - threshold) / threshold, 1.0)
                
                anomalies.append(Anomaly(
                    index=i,
                    value=value,
                    expected_value=mean,
                    deviation=abs(value - mean),
                    severity=severity,
                    anomaly_type=anomaly_type,
                    confidence=confidence
                ))
        
        anomaly_rate = (len(anomalies) / n) * 100 if n > 0 else 0.0
        
        summary = self._generate_summary(len(anomalies), n, anomaly_rate)
        
        return AnomalyResult(
            method=AnomalyMethod.Z_SCORE,
            anomalies=sorted(anomalies, key=lambda a: a.severity, reverse=True),
            total_points=n,
            anomaly_rate=anomaly_rate,
            summary=summary
        )
    
    def _detect_iqr(
        self,
        data: List[float],
        multiplier: Optional[float] = None
    ) -> AnomalyResult:
        """
        Detect anomalies using IQR (Interquartile Range) method.
        
        Points outside [Q1 - k*IQR, Q3 + k*IQR] are considered anomalies.
        More robust to outliers than z-score method.
        
        Args:
            data: List of numeric values
            multiplier: IQR multiplier (uses default if not specified)
        
        Returns:
            AnomalyResult object
        """
        multiplier = multiplier or self.iqr_multiplier
        n = len(data)
        sorted_data = sorted(data)
        
        # Calculate quartiles
        q1_index = n // 4
        q3_index = 3 * n // 4
        q1 = sorted_data[q1_index]
        q3 = sorted_data[q3_index]
        iqr = q3 - q1
        
        # Calculate bounds
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        # Calculate median for expected value
        median_index = n // 2
        if n % 2 == 0:
            median = (sorted_data[median_index - 1] + sorted_data[median_index]) / 2
        else:
            median = sorted_data[median_index]
        
        # Identify anomalies
        anomalies = []
        for i, value in enumerate(data):
            if value < lower_bound or value > upper_bound:
                # Determine anomaly type
                if value > upper_bound:
                    anomaly_type = AnomalyType.HIGH
                    deviation = value - upper_bound
                else:
                    anomaly_type = AnomalyType.LOW
                    deviation = lower_bound - value
                
                # Calculate severity based on distance from bounds
                if iqr > 0:
                    severity = min(deviation / (iqr * multiplier), 1.0)
                else:
                    severity = 1.0
                
                # Confidence based on how far outside bounds
                if iqr > 0:
                    confidence = min(deviation / iqr, 1.0)
                else:
                    confidence = 1.0
                
                anomalies.append(Anomaly(
                    index=i,
                    value=value,
                    expected_value=median,
                    deviation=deviation,
                    severity=severity,
                    anomaly_type=anomaly_type,
                    confidence=confidence
                ))
        
        anomaly_rate = (len(anomalies) / n) * 100 if n > 0 else 0.0
        summary = self._generate_summary(len(anomalies), n, anomaly_rate)
        
        return AnomalyResult(
            method=AnomalyMethod.IQR,
            anomalies=sorted(anomalies, key=lambda a: a.severity, reverse=True),
            total_points=n,
            anomaly_rate=anomaly_rate,
            summary=summary
        )
    
    def _detect_moving_average(
        self,
        data: List[float],
        window_size: int = 5,
        threshold: float = 2.0
    ) -> AnomalyResult:
        """
        Detect anomalies using moving average method.
        
        Compares each point to moving average of surrounding points.
        Good for time series data.
        
        Args:
            data: List of numeric values (time-ordered)
            window_size: Size of moving average window
            threshold: Threshold multiplier for standard deviation
        
        Returns:
            AnomalyResult object
        """
        n = len(data)
        
        if n < window_size:
            raise ValueError(f"Need at least {window_size} data points for moving average")
        
        anomalies = []
        
        # Calculate moving average and detect anomalies
        for i in range(n):
            # Get window (centered if possible)
            half_window = window_size // 2
            start = max(0, i - half_window)
            end = min(n, i + half_window + 1)
            window = data[start:end]
            
            # Calculate moving average and std dev
            ma = sum(window) / len(window)
            variance = sum((x - ma) ** 2 for x in window) / len(window)
            std_dev = math.sqrt(variance)
            
            # Check if current point is anomalous
            if std_dev > 0:
                deviation = abs(data[i] - ma)
                z_score = deviation / std_dev
                
                if z_score > threshold:
                    # Determine type (spike vs drop relative to previous)
                    if i > 0:
                        if data[i] > data[i-1]:
                            anomaly_type = AnomalyType.SPIKE
                        else:
                            anomaly_type = AnomalyType.DROP
                    else:
                        anomaly_type = AnomalyType.HIGH if data[i] > ma else AnomalyType.LOW
                    
                    severity = min(z_score / (threshold * 2), 1.0)
                    confidence = min((z_score - threshold) / threshold, 1.0)
                    
                    anomalies.append(Anomaly(
                        index=i,
                        value=data[i],
                        expected_value=ma,
                        deviation=deviation,
                        severity=severity,
                        anomaly_type=anomaly_type,
                        confidence=confidence
                    ))
        
        anomaly_rate = (len(anomalies) / n) * 100 if n > 0 else 0.0
        summary = self._generate_summary(len(anomalies), n, anomaly_rate)
        
        return AnomalyResult(
            method=AnomalyMethod.MOVING_AVERAGE,
            anomalies=sorted(anomalies, key=lambda a: a.severity, reverse=True),
            total_points=n,
            anomaly_rate=anomaly_rate,
            summary=summary
        )
    
    def _detect_threshold(
        self,
        data: List[float],
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> AnomalyResult:
        """
        Detect anomalies using simple threshold method.
        
        Points below min_value or above max_value are anomalies.
        
        Args:
            data: List of numeric values
            min_value: Minimum acceptable value (optional)
            max_value: Maximum acceptable value (optional)
        
        Returns:
            AnomalyResult object
        
        Raises:
            ValueError: If neither threshold is provided
        """
        if min_value is None and max_value is None:
            raise ValueError("Must provide at least one threshold (min_value or max_value)")
        
        n = len(data)
        anomalies = []
        
        # Calculate expected value (midpoint of thresholds or mean)
        if min_value is not None and max_value is not None:
            expected = (min_value + max_value) / 2
        else:
            expected = sum(data) / n
        
        for i, value in enumerate(data):
            is_anomaly = False
            deviation = 0.0
            anomaly_type = AnomalyType.HIGH
            
            if min_value is not None and value < min_value:
                is_anomaly = True
                deviation = min_value - value
                anomaly_type = AnomalyType.LOW
            elif max_value is not None and value > max_value:
                is_anomaly = True
                deviation = value - max_value
                anomaly_type = AnomalyType.HIGH
            
            if is_anomaly:
                # Severity based on distance from threshold
                threshold_range = (max_value - min_value) if (min_value and max_value) else abs(expected)
                if threshold_range > 0:
                    severity = min(deviation / threshold_range, 1.0)
                else:
                    severity = 1.0
                
                confidence = 1.0  # High confidence for threshold method
                
                anomalies.append(Anomaly(
                    index=i,
                    value=value,
                    expected_value=expected,
                    deviation=deviation,
                    severity=severity,
                    anomaly_type=anomaly_type,
                    confidence=confidence
                ))
        
        anomaly_rate = (len(anomalies) / n) * 100 if n > 0 else 0.0
        summary = self._generate_summary(len(anomalies), n, anomaly_rate)
        
        return AnomalyResult(
            method=AnomalyMethod.THRESHOLD,
            anomalies=sorted(anomalies, key=lambda a: a.severity, reverse=True),
            total_points=n,
            anomaly_rate=anomaly_rate,
            summary=summary
        )
    
    def _generate_summary(self, anomaly_count: int, total: int, rate: float) -> str:
        """Generate human-readable summary."""
        if anomaly_count == 0:
            return f"No anomalies detected in {total} data points"
        elif anomaly_count == 1:
            return f"1 anomaly detected ({rate:.1f}% of {total} points)"
        else:
            return f"{anomaly_count} anomalies detected ({rate:.1f}% of {total} points)"


# Global singleton instance
_anomaly_detector_instance: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """
    Get the global AnomalyDetector instance.
    
    Returns:
        AnomalyDetector singleton
    """
    global _anomaly_detector_instance
    if _anomaly_detector_instance is None:
        _anomaly_detector_instance = AnomalyDetector()
    return _anomaly_detector_instance


# Convenience function
def detect_anomalies(
    data: List[float],
    method: AnomalyMethod = AnomalyMethod.Z_SCORE,
    **kwargs
) -> AnomalyResult:
    """
    Detect anomalies in data.
    
    Args:
        data: List of numeric values
        method: Detection method
        **kwargs: Method-specific parameters
    
    Returns:
        AnomalyResult object
    """
    return get_anomaly_detector().detect_anomalies(data, method=method, **kwargs)
