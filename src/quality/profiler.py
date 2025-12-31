"""
Data Profiler - Phase 3: Automatic data pattern discovery

This module analyzes data to discover patterns, distributions, and anomalies.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
import re
import logging
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class ColumnProfile:
    """Profile of a single column"""
    column_name: str
    data_type: str
    total_rows: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    
    # Statistics (for numeric columns)
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    
    # Patterns
    sample_values: List[Any] = field(default_factory=list)
    value_distribution: Dict[Any, int] = field(default_factory=dict)
    detected_patterns: List[str] = field(default_factory=list)
    
    # Quality indicators
    has_outliers: bool = False
    suspected_issues: List[str] = field(default_factory=list)


@dataclass
class TableProfile:
    """Complete profile of a table"""
    table_name: str
    row_count: int
    column_count: int
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)
    relationships: List[Dict] = field(default_factory=list)
    profiled_at: Optional[datetime] = None
    
    @property
    def quality_score(self) -> float:
        """Calculate overall quality score"""
        if not self.columns:
            return 0.0
        
        scores = []
        for col in self.columns.values():
            # Score based on completeness
            completeness = 1.0 - col.null_percentage
            scores.append(completeness)
        
        return sum(scores) / len(scores)


class DataProfiler:
    """
    Automatic data profiling and pattern discovery.
    
    Features:
    - Column type detection
    - Distribution analysis
    - Pattern recognition (emails, phones, dates, etc.)
    - Relationship discovery
    - Anomaly detection
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # Pattern definitions
        self.patterns = {
            'email': r'^[\w\.-]+@[\w\.-]+\.\w+$',
            'phone_us': r'^\+?1?\d{10}$',
            'zip_code': r'^\d{5}(-\d{4})?$',
            'credit_card': r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$',
            'url': r'^https?://[\w\.-]+\.\w+',
            'ipv4': r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
            'date_iso': r'^\d{4}-\d{2}-\d{2}$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        }
        
        # Profile cache
        self.profiles: Dict[str, TableProfile] = {}
        
        logger.info("Data Profiler initialized")
    
    def profile_table(
        self,
        table_name: str,
        data: List[Dict],
        sample_size: int = 100
    ) -> TableProfile:
        """
        Profile a table's data
        
        Args:
            table_name: Name of the table
            data: List of row dictionaries
            sample_size: Number of sample values to store per column
            
        Returns:
            TableProfile with complete analysis
        """
        logger.info(f"Profiling table: {table_name}")
        
        if not data:
            return TableProfile(
                table_name=table_name,
                row_count=0,
                column_count=0,
                profiled_at=datetime.now()
            )
        
        row_count = len(data)
        columns = list(data[0].keys()) if data else []
        column_count = len(columns)
        
        # Profile each column
        column_profiles = {}
        for col_name in columns:
            profile = self._profile_column(col_name, data, sample_size)
            column_profiles[col_name] = profile
        
        # Detect relationships (simple version)
        relationships = self._detect_relationships(column_profiles)
        
        table_profile = TableProfile(
            table_name=table_name,
            row_count=row_count,
            column_count=column_count,
            columns=column_profiles,
            relationships=relationships,
            profiled_at=datetime.now()
        )
        
        # Cache the profile
        self.profiles[table_name] = table_profile
        
        return table_profile
    
    def _profile_column(
        self,
        column_name: str,
        data: List[Dict],
        sample_size: int
    ) -> ColumnProfile:
        """Profile a single column"""
        # Extract column values
        values = [row.get(column_name) for row in data]
        total = len(values)
        
        # Count nulls
        null_values = [v for v in values if v is None or v == '']
        null_count = len(null_values)
        null_pct = (null_count / total * 100) if total > 0 else 0
        
        # Non-null values
        non_null_values = [v for v in values if v is not None and v != '']
        
        # Count unique
        unique_count = len(set(non_null_values))
        unique_pct = (unique_count / total * 100) if total > 0 else 0
        
        # Detect data type
        data_type = self._detect_type(non_null_values)
        
        # Calculate statistics for numeric columns
        min_val, max_val, mean_val, median_val, std_dev = None, None, None, None, None
        if data_type in ['integer', 'decimal'] and non_null_values:
            try:
                numeric_values = [float(v) for v in non_null_values if isinstance(v, (int, float))]
                if numeric_values:
                    min_val = min(numeric_values)
                    max_val = max(numeric_values)
                    mean_val = sum(numeric_values) / len(numeric_values)
                    median_val = sorted(numeric_values)[len(numeric_values) // 2]
            except Exception as e:
                logger.warning(f"Error calculating statistics for {column_name}: {e}")
        
        # Get sample values and distribution
        sample_values = non_null_values[:sample_size]
        value_counts = Counter(non_null_values)
        top_values = dict(value_counts.most_common(20))
        
        # Detect patterns
        detected_patterns = self._detect_patterns(non_null_values)
        
        # Detect issues
        suspected_issues = []
        if null_pct > 50:
            suspected_issues.append(f"High null percentage: {null_pct:.1f}%")
        if unique_pct < 1 and total > 100:
            suspected_issues.append(f"Very low cardinality: {unique_count} unique values")
        
        return ColumnProfile(
            column_name=column_name,
            data_type=data_type,
            total_rows=total,
            null_count=null_count,
            null_percentage=null_pct,
            unique_count=unique_count,
            unique_percentage=unique_pct,
            min_value=min_val,
            max_value=max_val,
            mean=mean_val,
            median=median_val,
            std_dev=std_dev,
            sample_values=sample_values,
            value_distribution=top_values,
            detected_patterns=detected_patterns,
            suspected_issues=suspected_issues
        )
    
    def _detect_type(self, values: List) -> str:
        """Detect column data type"""
        if not values:
            return 'unknown'
        
        # Sample a few values
        sample = values[:min(100, len(values))]
        
        # Check types
        int_count = sum(1 for v in sample if isinstance(v, int))
        float_count = sum(1 for v in sample if isinstance(v, float))
        bool_count = sum(1 for v in sample if isinstance(v, bool))
        str_count = sum(1 for v in sample if isinstance(v, str))
        
        total_sample = len(sample)
        
        # Determine type based on majority
        if bool_count / total_sample > 0.8:
            return 'boolean'
        elif (int_count + float_count) / total_sample > 0.8:
            return 'decimal' if float_count > int_count else 'integer'
        elif str_count / total_sample > 0.5:
            return 'string'
        else:
            return 'mixed'
    
    def _detect_patterns(self, values: List) -> List[str]:
        """Detect common patterns in string values"""
        detected = []
        
        if not values:
            return detected
        
        # Sample string values
        str_values = [str(v) for v in values[:100] if v]
        
        # Test each pattern
        for pattern_name, pattern_regex in self.patterns.items():
            matches = sum(1 for v in str_values if re.match(pattern_regex, v, re.IGNORECASE))
            match_pct = (matches / len(str_values)) if str_values else 0
            
            if match_pct > 0.8:  # 80% of values match pattern
                detected.append(pattern_name)
        
        return detected
    
    def _detect_relationships(
        self,
        column_profiles: Dict[str, ColumnProfile]
    ) -> List[Dict]:
        """Detect potential relationships between columns"""
        relationships = []
        
        # Look for potential foreign keys
        for col_name, profile in column_profiles.items():
            # Potential FK if column name ends with _id and has high uniqueness
            if (col_name.endswith('_id') or col_name.endswith('_key')) and profile.unique_percentage > 80:
                relationships.append({
                    'type': 'potential_foreign_key',
                    'column': col_name,
                    'confidence': 0.8
                })
        
        return relationships
    
    def get_profile(self, table_name: str) -> Optional[TableProfile]:
        """Get cached profile for a table"""
        return self.profiles.get(table_name)
    
    def get_all_profiles(self) -> Dict[str, TableProfile]:
        """Get all cached profiles"""
        return self.profiles.copy()
    
    def detect_anomalies(
        self,
        table_name: str,
        column_name: str
    ) -> List[Dict]:
        """
        Detect anomalies in a specific column
        
        Returns:
            List of detected anomalies with details
        """
        profile = self.profiles.get(table_name)
        if not profile or column_name not in profile.columns:
            return []
        
        col_profile = profile.columns[column_name]
        anomalies = []
        
        # Check for high null rate
        if col_profile.null_percentage > 30:
            anomalies.append({
                'type': 'high_nulls',
                'severity': 'warning',
                'description': f"Column has {col_profile.null_percentage:.1f}% null values",
                'recommendation': "Consider imputation or flagging missing data"
            })
        
        # Check for low cardinality
        if col_profile.unique_percentage < 5 and col_profile.total_rows > 1000:
            anomalies.append({
                'type': 'low_cardinality',
                'severity': 'info',
                'description': f"Only {col_profile.unique_count} unique values in {col_profile.total_rows} rows",
                'recommendation': "Consider if this should be a dimension/category"
            })
        
        return anomalies
    
    def compare_profiles(
        self,
        table1: str,
        table2: str
    ) -> Dict:
        """
        Compare profiles of two tables to find similarities
        (Useful for multi-source matching)
        """
        profile1 = self.profiles.get(table1)
        profile2 = self.profiles.get(table2)
        
        if not profile1 or not profile2:
            return {'error': 'One or both profiles not found'}
        
        common_columns = set(profile1.columns.keys()) & set(profile2.columns.keys())
        similar_columns = []
        
        for col in common_columns:
            col1 = profile1.columns[col]
            col2 = profile2.columns[col]
            
            # Check if columns are similar
            if col1.data_type == col2.data_type:
                similar_columns.append({
                    'column': col,
                    'data_type': col1.data_type,
                    'table1_unique': col1.unique_count,
                    'table2_unique': col2.unique_count
                })
        
        return {
            'table1': table1,
            'table2': table2,
            'common_columns': list(common_columns),
            'similar_columns': similar_columns,
            'potential_join_keys': [
                col for col in common_columns
                if profile1.columns[col].unique_percentage > 90
                and profile2.columns[col].unique_percentage > 90
            ]
        }


# Singleton instance
_profiler = None

def get_data_profiler() -> DataProfiler:
    """Get the singleton DataProfiler instance"""
    global _profiler
    if _profiler is None:
        _profiler = DataProfiler()
    return _profiler
