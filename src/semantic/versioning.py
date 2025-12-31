"""
Semantic Layer Versioning - A/B Testing and Version Management

Manage multiple versions of semantic layer for:
- A/B testing new definitions
- Rolling back bad changes
- Gradual rollout of new metrics
- Tracking which version performs better
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.semantic.loader import get_semantic_layer, SemanticLayer


class SemanticLayerVersion(str, Enum):
    """Semantic layer versions."""
    
    V1_ORIGINAL = "v1"
    V2_IMPROVED_SYNONYMS = "v2"
    V3_NEW_METRICS = "v3"
    EXPERIMENTAL = "experimental"


class VersionStrategy(str, Enum):
    """Version rollout strategy."""
    
    PERCENTAGE = "percentage"  # Hash-based % rollout
    USER_LIST = "user_list"    # Specific user IDs
    ROLE_BASED = "role_based"  # Based on user role
    DEPARTMENT = "department"  # Based on department


class VersionConfig(BaseModel):
    """Configuration for a semantic layer version."""
    
    version: str
    name: str
    description: str
    active: bool = True
    rollout_percentage: int = 0  # 0-100
    target_users: List[str] = []
    target_roles: List[str] = []
    target_departments: List[str] = []
    config_path: Optional[str] = None
    created_at: datetime
    metrics_changed: List[str] = []
    dimensions_changed: List[str] = []


class ExperimentMetrics(BaseModel):
    """Metrics tracking for version experiments."""
    
    version: str
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_response_time_ms: float = 0.0
    user_satisfaction: float = 0.0  # 0-1 scale
    correction_rate: float = 0.0    # % of queries needing correction


class SemanticLayerVersionManager:
    """
    Manage multiple versions of semantic layer.
    
    Features:
    - A/B testing with controlled rollout
    - Performance tracking per version
    - Automatic version assignment
    - Rollback capability
    """
    
    def __init__(self):
        """Initialize version manager."""
        self.versions: Dict[str, VersionConfig] = {}
        self.active_experiments: Dict[str, str] = {}  # user_id -> version
        self.experiment_metrics: Dict[str, ExperimentMetrics] = {}
        self.default_version = SemanticLayerVersion.V1_ORIGINAL.value
        
        # Initialize default version
        self._initialize_default_versions()
    
    def _initialize_default_versions(self):
        """Initialize default version configurations."""
        self.versions[SemanticLayerVersion.V1_ORIGINAL.value] = VersionConfig(
            version=SemanticLayerVersion.V1_ORIGINAL.value,
            name="Original",
            description="Original semantic layer configuration",
            active=True,
            rollout_percentage=100,
            created_at=datetime.utcnow()
        )
        
        self.experiment_metrics[SemanticLayerVersion.V1_ORIGINAL.value] = ExperimentMetrics(
            version=SemanticLayerVersion.V1_ORIGINAL.value
        )
    
    def register_version(
        self,
        version: str,
        name: str,
        description: str,
        rollout_percentage: int = 0,
        target_users: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        config_path: Optional[str] = None
    ) -> VersionConfig:
        """
        Register a new semantic layer version.
        
        Args:
            version: Version identifier (e.g., "v2", "experimental")
            name: Human-readable name
            description: Description of changes
            rollout_percentage: Percentage of users to receive this version (0-100)
            target_users: Specific user IDs to include
            target_roles: Specific roles to include
            config_path: Path to alternative semantic layer config
        
        Returns:
            VersionConfig object
        """
        config = VersionConfig(
            version=version,
            name=name,
            description=description,
            rollout_percentage=rollout_percentage,
            target_users=target_users or [],
            target_roles=target_roles or [],
            config_path=config_path,
            created_at=datetime.utcnow()
        )
        
        self.versions[version] = config
        self.experiment_metrics[version] = ExperimentMetrics(version=version)
        
        return config
    
    def get_version_for_user(
        self,
        user_id: str,
        user_role: Optional[str] = None,
        user_department: Optional[str] = None
    ) -> str:
        """
        Determine which semantic layer version to serve to a user.
        
        Priority:
        1. User explicitly assigned to experiment
        2. User in target_users list
        3. User role in target_roles list
        4. Hash-based percentage rollout
        5. Default version
        
        Args:
            user_id: User identifier
            user_role: User's role
            user_department: User's department
        
        Returns:
            Version identifier to use
        """
        # Check if user is explicitly assigned
        if user_id in self.active_experiments:
            return self.active_experiments[user_id]
        
        # Check all active versions
        for version_id, config in self.versions.items():
            if not config.active or version_id == self.default_version:
                continue
            
            # Check if user is in target list
            if user_id in config.target_users:
                self.active_experiments[user_id] = version_id
                return version_id
            
            # Check if user's role is targeted
            if user_role and user_role in config.target_roles:
                self.active_experiments[user_id] = version_id
                return version_id
            
            # Check if user's department is targeted
            if user_department and user_department in config.target_departments:
                self.active_experiments[user_id] = version_id
                return version_id
            
            # Check percentage rollout
            if config.rollout_percentage > 0:
                # Use hash for deterministic assignment
                hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
                user_bucket = hash_val % 100
                
                if user_bucket < config.rollout_percentage:
                    self.active_experiments[user_id] = version_id
                    return version_id
        
        # Return default version
        return self.default_version
    
    def assign_user_to_version(self, user_id: str, version: str):
        """
        Explicitly assign a user to a version.
        
        Args:
            user_id: User identifier
            version: Version to assign
        """
        if version not in self.versions:
            raise ValueError(f"Unknown version: {version}")
        
        self.active_experiments[user_id] = version
    
    def remove_user_from_experiment(self, user_id: str):
        """Remove user from explicit version assignment."""
        if user_id in self.active_experiments:
            del self.active_experiments[user_id]
    
    def record_query(
        self,
        user_id: str,
        version: str,
        success: bool,
        response_time_ms: float,
        needed_correction: bool = False
    ):
        """
        Track query performance for a version.
        
        Args:
            user_id: User who ran the query
            version: Version used
            success: Whether query succeeded
            response_time_ms: Query response time
            needed_correction: Whether user had to correct the result
        """
        if version not in self.experiment_metrics:
            self.experiment_metrics[version] = ExperimentMetrics(version=version)
        
        metrics = self.experiment_metrics[version]
        
        # Update counts
        metrics.total_queries += 1
        if success:
            metrics.successful_queries += 1
        else:
            metrics.failed_queries += 1
        
        # Update average response time
        # Running average: new_avg = old_avg + (new_value - old_avg) / n
        metrics.avg_response_time_ms += (
            response_time_ms - metrics.avg_response_time_ms
        ) / metrics.total_queries
        
        # Update correction rate
        if needed_correction:
            correction_count = metrics.correction_rate * (metrics.total_queries - 1) + 1
            metrics.correction_rate = correction_count / metrics.total_queries
    
    def record_user_feedback(
        self,
        user_id: str,
        version: str,
        satisfaction_score: float  # 0-1 scale
    ):
        """
        Record user satisfaction feedback.
        
        Args:
            user_id: User providing feedback
            version: Version being rated
            satisfaction_score: 0-1 scale (0=bad, 1=excellent)
        """
        if version not in self.experiment_metrics:
            return
        
        metrics = self.experiment_metrics[version]
        
        # Update running average of satisfaction
        if metrics.total_queries > 0:
            metrics.user_satisfaction += (
                satisfaction_score - metrics.user_satisfaction
            ) / metrics.total_queries
    
    def get_version_performance(self, version: str) -> Optional[ExperimentMetrics]:
        """Get performance metrics for a version."""
        return self.experiment_metrics.get(version)
    
    def compare_versions(
        self,
        version_a: str,
        version_b: str
    ) -> Dict[str, Any]:
        """
        Compare performance between two versions.
        
        Returns:
            Comparison metrics showing which version performs better
        """
        metrics_a = self.experiment_metrics.get(version_a)
        metrics_b = self.experiment_metrics.get(version_b)
        
        if not metrics_a or not metrics_b:
            return {"error": "One or both versions have no metrics"}
        
        # Calculate success rates
        success_rate_a = (
            metrics_a.successful_queries / metrics_a.total_queries 
            if metrics_a.total_queries > 0 else 0
        )
        success_rate_b = (
            metrics_b.successful_queries / metrics_b.total_queries 
            if metrics_b.total_queries > 0 else 0
        )
        
        return {
            "version_a": {
                "version": version_a,
                "total_queries": metrics_a.total_queries,
                "success_rate": success_rate_a,
                "avg_response_time_ms": metrics_a.avg_response_time_ms,
                "user_satisfaction": metrics_a.user_satisfaction,
                "correction_rate": metrics_a.correction_rate
            },
            "version_b": {
                "version": version_b,
                "total_queries": metrics_b.total_queries,
                "success_rate": success_rate_b,
                "avg_response_time_ms": metrics_b.avg_response_time_ms,
                "user_satisfaction": metrics_b.user_satisfaction,
                "correction_rate": metrics_b.correction_rate
            },
            "winner": self._determine_winner(metrics_a, metrics_b)
        }
    
    def _determine_winner(
        self,
        metrics_a: ExperimentMetrics,
        metrics_b: ExperimentMetrics
    ) -> str:
        """
        Determine which version is performing better.
        
        Scoring criteria:
        - Success rate (40%)
        - User satisfaction (30%)
        - Low correction rate (20%)
        - Response time (10%)
        """
        # Calculate success rates
        success_rate_a = (
            metrics_a.successful_queries / metrics_a.total_queries 
            if metrics_a.total_queries > 0 else 0
        )
        success_rate_b = (
            metrics_b.successful_queries / metrics_b.total_queries 
            if metrics_b.total_queries > 0 else 0
        )
        
        # Normalize response times (lower is better)
        max_time = max(metrics_a.avg_response_time_ms, metrics_b.avg_response_time_ms)
        if max_time > 0:
            time_score_a = 1 - (metrics_a.avg_response_time_ms / max_time)
            time_score_b = 1 - (metrics_b.avg_response_time_ms / max_time)
        else:
            time_score_a = time_score_b = 0.5
        
        # Calculate weighted scores
        score_a = (
            success_rate_a * 0.4 +
            metrics_a.user_satisfaction * 0.3 +
            (1 - metrics_a.correction_rate) * 0.2 +
            time_score_a * 0.1
        )
        
        score_b = (
            success_rate_b * 0.4 +
            metrics_b.user_satisfaction * 0.3 +
            (1 - metrics_b.correction_rate) * 0.2 +
            time_score_b * 0.1
        )
        
        if score_a > score_b:
            return metrics_a.version
        elif score_b > score_a:
            return metrics_b.version
        else:
            return "tie"
    
    def promote_version(self, version: str, rollout_percentage: int = 100):
        """
        Promote a version to wider rollout.
        
        Args:
            version: Version to promote
            rollout_percentage: New rollout percentage (0-100)
        """
        if version not in self.versions:
            raise ValueError(f"Unknown version: {version}")
        
        self.versions[version].rollout_percentage = rollout_percentage
    
    def rollback_version(self, version: str):
        """
        Rollback a version (set rollout to 0%, deactivate).
        
        Args:
            version: Version to rollback
        """
        if version not in self.versions:
            raise ValueError(f"Unknown version: {version}")
        
        self.versions[version].active = False
        self.versions[version].rollout_percentage = 0
        
        # Remove users from this experiment
        users_to_remove = [
            uid for uid, ver in self.active_experiments.items()
            if ver == version
        ]
        for uid in users_to_remove:
            del self.active_experiments[uid]
    
    def get_all_versions(self) -> List[VersionConfig]:
        """Get list of all registered versions."""
        return list(self.versions.values())


# Singleton instance
_version_manager_instance: Optional[SemanticLayerVersionManager] = None


def get_version_manager() -> SemanticLayerVersionManager:
    """
    Get or create the global SemanticLayerVersionManager instance.
    
    Returns:
        SemanticLayerVersionManager singleton
    """
    global _version_manager_instance
    if _version_manager_instance is None:
        _version_manager_instance = SemanticLayerVersionManager()
    return _version_manager_instance
