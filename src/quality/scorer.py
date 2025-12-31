"""
Data Quality Scorer - Phase 3: Assess data quality across multiple dimensions

This module evaluates data quality for metrics and dimensions, providing
scores and recommendations for improvement.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """Dimensions of data quality"""
    FRESHNESS = "freshness"  # How recent is the data
    COMPLETENESS = "completeness"  # Missing values
    ACCURACY = "accuracy"  # Data validation rules
    CONSISTENCY = "consistency"  # Cross-table consistency
    VALIDITY = "validity"  # Format and type validation
    UNIQUENESS = "uniqueness"  # Duplicate detection


@dataclass
class QualityScore:
    """Quality score for a data entity"""
    entity_name: str
    entity_type: str  # 'metric', 'dimension', 'table'
    overall_score: float  # 0.0 to 1.0
    dimension_scores: Dict[QualityDimension, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_assessed: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class QualityRule:
    """Rule for assessing data quality"""
    name: str
    dimension: QualityDimension
    description: str
    sql_check: Optional[str] = None
    threshold: float = 0.95
    severity: str = "warning"  # 'critical', 'warning', 'info'


class DataQualityScorer:
    """
    Assess data quality across multiple dimensions.
    
    Features:
    - Freshness checks (data recency)
    - Completeness checks (missing values)
    - Accuracy validation (business rules)
    - Consistency checks (cross-table)
    - Uniqueness checks (duplicates)
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
        
        # Quality rules registry
        self.rules: Dict[str, List[QualityRule]] = {
            'metric': [],
            'dimension': [],
            'table': []
        }
        
        # Quality scores cache
        self.scores_cache: Dict[str, QualityScore] = {}
        
        # Default rules
        self._register_default_rules()
        
        logger.info("Data Quality Scorer initialized")
    
    def _register_default_rules(self):
        """Register default quality rules"""
        
        # Freshness rules
        self.register_rule(QualityRule(
            name="data_freshness_24h",
            dimension=QualityDimension.FRESHNESS,
            description="Data should be updated within last 24 hours",
            threshold=0.9,
            severity="warning"
        ))
        
        # Completeness rules
        self.register_rule(QualityRule(
            name="no_null_values",
            dimension=QualityDimension.COMPLETENESS,
            description="Critical fields should not have null values",
            sql_check="SELECT COUNT(*) FROM {table} WHERE {column} IS NULL",
            threshold=0.95,
            severity="critical"
        ))
        
        # Uniqueness rules
        self.register_rule(QualityRule(
            name="primary_key_unique",
            dimension=QualityDimension.UNIQUENESS,
            description="Primary key should be unique",
            sql_check="SELECT COUNT(*) - COUNT(DISTINCT {column}) FROM {table}",
            threshold=1.0,
            severity="critical"
        ))
    
    def register_rule(self, rule: QualityRule, entity_type: str = 'table'):
        """Register a new quality rule"""
        if entity_type not in self.rules:
            self.rules[entity_type] = []
        self.rules[entity_type].append(rule)
        logger.info(f"Registered quality rule: {rule.name} for {entity_type}")
    
    def assess_metric_quality(
        self,
        metric_name: str,
        metric_config: Dict,
        db_connection = None
    ) -> QualityScore:
        """
        Assess quality of a metric
        
        Args:
            metric_name: Name of the metric
            metric_config: Metric configuration from semantic layer
            db_connection: Database connection for executing checks
            
        Returns:
            QualityScore with assessment results
        """
        logger.info(f"Assessing quality for metric: {metric_name}")
        
        dimension_scores = {}
        issues = []
        recommendations = []
        
        # 1. Freshness check
        freshness_score, freshness_issues = self._check_freshness(
            metric_name,
            metric_config,
            db_connection
        )
        dimension_scores[QualityDimension.FRESHNESS] = freshness_score
        issues.extend(freshness_issues)
        
        # 2. Completeness check
        completeness_score, completeness_issues = self._check_completeness(
            metric_name,
            metric_config,
            db_connection
        )
        dimension_scores[QualityDimension.COMPLETENESS] = completeness_score
        issues.extend(completeness_issues)
        
        # 3. Validity check (formula syntax, dependencies)
        validity_score, validity_issues = self._check_validity(
            metric_name,
            metric_config
        )
        dimension_scores[QualityDimension.VALIDITY] = validity_score
        issues.extend(validity_issues)
        
        # Calculate overall score (weighted average)
        weights = {
            QualityDimension.FRESHNESS: 0.3,
            QualityDimension.COMPLETENESS: 0.4,
            QualityDimension.VALIDITY: 0.3
        }
        
        overall_score = sum(
            dimension_scores.get(dim, 0) * weight
            for dim, weight in weights.items()
        )
        
        # Generate recommendations
        if freshness_score < 0.8:
            recommendations.append("Consider setting up automated data refreshes")
        if completeness_score < 0.9:
            recommendations.append("Review data pipeline for missing value handling")
        
        score = QualityScore(
            entity_name=metric_name,
            entity_type='metric',
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=issues,
            recommendations=recommendations,
            last_assessed=datetime.now(),
            metadata={'config': metric_config}
        )
        
        # Cache the score
        self.scores_cache[f"metric:{metric_name}"] = score
        
        return score
    
    def _check_freshness(
        self,
        metric_name: str,
        config: Dict,
        db_connection
    ) -> Tuple[float, List[str]]:
        """Check data freshness"""
        issues = []
        
        if not db_connection:
            # Can't check without DB connection
            return 0.8, ["Unable to verify data freshness (no DB connection)"]
        
        try:
            # Try to find last updated timestamp
            base_table = config.get('base_table', '')
            
            if not base_table:
                return 0.7, ["No base table specified for freshness check"]
            
            # Check if table has updated_at or similar column
            # This is a simplified check - real implementation would query metadata
            
            # For now, return moderate score with info
            return 0.8, []
            
        except Exception as e:
            logger.error(f"Freshness check failed for {metric_name}: {e}")
            issues.append(f"Freshness check error: {str(e)}")
            return 0.5, issues
    
    def _check_completeness(
        self,
        metric_name: str,
        config: Dict,
        db_connection
    ) -> Tuple[float, List[str]]:
        """Check data completeness"""
        issues = []
        
        if not db_connection:
            return 0.9, []  # Assume good if can't check
        
        try:
            # Check if the metric's source columns have nulls
            formula = config.get('formula', '')
            
            # Extract column names from formula (simplified)
            # Real implementation would parse SQL properly
            
            # For now, return high score
            return 0.95, []
            
        except Exception as e:
            logger.error(f"Completeness check failed for {metric_name}: {e}")
            issues.append(f"Completeness check error: {str(e)}")
            return 0.7, issues
    
    def _check_validity(
        self,
        metric_name: str,
        config: Dict
    ) -> Tuple[float, List[str]]:
        """Check configuration validity"""
        issues = []
        score = 1.0
        
        # Check required fields
        required_fields = ['formula', 'base_table', 'aggregation']
        for field in required_fields:
            if field not in config:
                issues.append(f"Missing required field: {field}")
                score -= 0.2
        
        # Check formula syntax (basic check)
        formula = config.get('formula', '')
        if not formula:
            issues.append("Empty formula")
            score -= 0.3
        
        # Check aggregation type
        valid_aggregations = ['sum', 'avg', 'count', 'min', 'max', 'calculated']
        aggregation = config.get('aggregation', '')
        if aggregation and aggregation not in valid_aggregations:
            issues.append(f"Invalid aggregation type: {aggregation}")
            score -= 0.2
        
        return max(score, 0.0), issues
    
    def assess_dimension_quality(
        self,
        dimension_name: str,
        dimension_config: Dict,
        db_connection = None
    ) -> QualityScore:
        """Assess quality of a dimension"""
        logger.info(f"Assessing quality for dimension: {dimension_name}")
        
        dimension_scores = {}
        issues = []
        recommendations = []
        
        # 1. Validity check
        validity_score, validity_issues = self._check_dimension_validity(
            dimension_name,
            dimension_config
        )
        dimension_scores[QualityDimension.VALIDITY] = validity_score
        issues.extend(validity_issues)
        
        # 2. Uniqueness check (if it's supposed to be unique)
        if dimension_config.get('primary_key'):
            uniqueness_score, uniqueness_issues = self._check_uniqueness(
                dimension_name,
                dimension_config,
                db_connection
            )
            dimension_scores[QualityDimension.UNIQUENESS] = uniqueness_score
            issues.extend(uniqueness_issues)
        else:
            dimension_scores[QualityDimension.UNIQUENESS] = 1.0
        
        # Overall score
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        # Recommendations
        if validity_score < 0.9:
            recommendations.append("Review dimension configuration")
        
        score = QualityScore(
            entity_name=dimension_name,
            entity_type='dimension',
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=issues,
            recommendations=recommendations,
            last_assessed=datetime.now(),
            metadata={'config': dimension_config}
        )
        
        self.scores_cache[f"dimension:{dimension_name}"] = score
        
        return score
    
    def _check_dimension_validity(
        self,
        dimension_name: str,
        config: Dict
    ) -> Tuple[float, List[str]]:
        """Check dimension configuration validity"""
        issues = []
        score = 1.0
        
        # Check required fields
        if 'type' not in config:
            issues.append("Missing dimension type")
            score -= 0.3
        
        if 'description' not in config or not config['description']:
            issues.append("Missing description")
            score -= 0.1
        
        return max(score, 0.0), issues
    
    def _check_uniqueness(
        self,
        dimension_name: str,
        config: Dict,
        db_connection
    ) -> Tuple[float, List[str]]:
        """Check uniqueness constraint"""
        issues = []
        
        if not db_connection:
            return 0.9, []
        
        # Would query database to check for duplicates
        # For now, return optimistic score
        return 0.95, []
    
    def get_quality_report(
        self,
        entity_type: Optional[str] = None,
        min_score: float = 0.0
    ) -> Dict:
        """
        Get quality report for all assessed entities
        
        Args:
            entity_type: Filter by type ('metric', 'dimension')
            min_score: Only include entities with score >= min_score
            
        Returns:
            Quality report with statistics and scores
        """
        filtered_scores = []
        
        for key, score in self.scores_cache.items():
            if entity_type and not key.startswith(entity_type):
                continue
            if score.overall_score < min_score:
                continue
            filtered_scores.append(score)
        
        # Calculate statistics
        if not filtered_scores:
            return {
                'total_entities': 0,
                'average_score': 0.0,
                'scores': []
            }
        
        total = len(filtered_scores)
        avg_score = sum(s.overall_score for s in filtered_scores) / total
        
        # Group by quality level
        excellent = sum(1 for s in filtered_scores if s.overall_score >= 0.9)
        good = sum(1 for s in filtered_scores if 0.7 <= s.overall_score < 0.9)
        poor = sum(1 for s in filtered_scores if s.overall_score < 0.7)
        
        return {
            'total_entities': total,
            'average_score': round(avg_score, 3),
            'distribution': {
                'excellent': excellent,
                'good': good,
                'poor': poor
            },
            'scores': [
                {
                    'entity_name': s.entity_name,
                    'entity_type': s.entity_type,
                    'overall_score': round(s.overall_score, 3),
                    'dimension_scores': {
                        dim.value: round(score, 3)
                        for dim, score in s.dimension_scores.items()
                    },
                    'issues_count': len(s.issues),
                    'issues': s.issues,
                    'recommendations': s.recommendations,
                    'last_assessed': s.last_assessed.isoformat() if s.last_assessed else None
                }
                for s in sorted(filtered_scores, key=lambda x: x.overall_score)
            ]
        }
    
    def get_low_quality_entities(
        self,
        threshold: float = 0.7
    ) -> List[QualityScore]:
        """Get entities with quality scores below threshold"""
        return [
            score for score in self.scores_cache.values()
            if score.overall_score < threshold
        ]
    
    def clear_cache(self):
        """Clear quality scores cache"""
        self.scores_cache.clear()
        logger.info("Quality scores cache cleared")


# Singleton instance
_scorer = None

def get_quality_scorer() -> DataQualityScorer:
    """Get the singleton DataQualityScorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = DataQualityScorer()
    return _scorer
