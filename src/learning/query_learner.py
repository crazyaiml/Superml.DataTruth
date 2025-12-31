"""
Query Learner

Learns from user queries to improve semantic layer mappings.
Tracks successful and failed queries to identify patterns.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Singleton instance
_query_learner = None


class QueryLearner:
    """
    Learns from user queries to improve semantic mappings.
    
    Features:
    1. Track successful query patterns
    2. Learn metric/dimension name variations
    3. Auto-generate synonyms from successful matches
    4. Identify commonly failed lookups
    """
    
    def __init__(self, vector_store=None):
        """
        Initialize query learner.
        
        Args:
            vector_store: Optional VectorStore instance for persistent learning
        """
        self.vector_store = vector_store
        self.query_history: List[Dict] = []
        self.successful_matches: Dict[str, List[str]] = defaultdict(list)  # actual_name -> [user_terms]
        self.failed_lookups: Dict[str, int] = defaultdict(int)  # user_term -> count
        self.learned_synonyms: Dict[str, List[str]] = defaultdict(list)  # actual_name -> [learned_synonyms]
        
        # Load learned synonyms from vector store if available
        if self.vector_store:
            try:
                # TODO: Load from vector store
                logger.info("QueryLearner initialized with vector store persistence")
            except Exception as e:
                logger.warning(f"Failed to load learned synonyms from vector store: {e}")
        
    def record_query(
        self,
        user_query: str,
        extracted_metric: Optional[str],
        extracted_dimensions: List[str],
        matched_metric: Optional[str],
        matched_dimensions: List[str],
        success: bool,
        connection_id: str
    ):
        """
        Record a query and its outcome for learning.
        
        Args:
            user_query: Original user query
            extracted_metric: Metric name extracted from query
            extracted_dimensions: Dimension names extracted
            matched_metric: Actual metric name matched (if any)
            matched_dimensions: Actual dimension names matched
            success: Whether query executed successfully
            connection_id: Database connection used
        """
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_query": user_query,
            "extracted_metric": extracted_metric,
            "extracted_dimensions": extracted_dimensions,
            "matched_metric": matched_metric,
            "matched_dimensions": matched_dimensions,
            "success": success,
            "connection_id": connection_id
        }
        
        self.query_history.append(record)
        
        # Learn from successful matches
        if success:
            if extracted_metric and matched_metric and extracted_metric.lower() != matched_metric.lower():
                # User term was different from actual metric name
                self.successful_matches[matched_metric].append(extracted_metric)
                self._learn_synonym(matched_metric, extracted_metric, connection_id)
            
            for i, extracted_dim in enumerate(extracted_dimensions):
                if i < len(matched_dimensions):
                    matched_dim = matched_dimensions[i]
                    if extracted_dim.lower() != matched_dim.lower():
                        self.successful_matches[matched_dim].append(extracted_dim)
                        self._learn_synonym(matched_dim, extracted_dim, connection_id)
            
            # Record successful query pattern to vector store
            if self.vector_store:
                try:
                    self.vector_store.record_successful_query(
                        connection_id=connection_id,
                        user_query=user_query,
                        metric=matched_metric or "",
                        dimensions=matched_dimensions
                    )
                except Exception as e:
                    logger.warning(f"Failed to record query to vector store: {e}")
        
        # Track failed lookups
        else:
            if extracted_metric:
                self.failed_lookups[extracted_metric] += 1
            for dim in extracted_dimensions:
                self.failed_lookups[dim] += 1
    
    def _learn_synonym(self, actual_name: str, user_term: str, connection_id: str = None):
        """
        Learn a new synonym from successful match.
        
        Args:
            actual_name: The actual field/metric name  
            user_term: The term user used
            connection_id: Optional connection ID for vector store
        """
        if user_term not in self.learned_synonyms[actual_name]:
            self.learned_synonyms[actual_name].append(user_term)
            logger.info(f"Learned synonym: '{user_term}' -> '{actual_name}'")
            
            # Persist to vector store if available
            if self.vector_store and connection_id:
                try:
                    self.vector_store.add_learned_synonym(
                        connection_id=connection_id,
                        user_term=user_term,
                        matched_field=actual_name,
                        field_type="metric",  # Could determine dynamically
                        context=f"Learned from successful query match"
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist learned synonym to vector store: {e}")
    
    def get_learned_synonyms(self, name: str) -> List[str]:
        """Get learned synonyms for a metric/dimension name."""
        return self.learned_synonyms.get(name, [])
    
    def get_all_learned_synonyms(self) -> Dict[str, List[str]]:
        """Get all learned synonyms."""
        return dict(self.learned_synonyms)
    
    def get_suggestions_for_failed_lookup(self, failed_term: str, available_names: List[str]) -> List[str]:
        """
        Get suggestions for a failed lookup based on learning.
        
        Args:
            failed_term: The term that failed to match
            available_names: List of available metric/dimension names
            
        Returns:
            List of suggested names
        """
        suggestions = []
        failed_lower = failed_term.lower()
        
        # Check if any available name has learned synonyms matching this term
        for name in available_names:
            learned_syns = self.get_learned_synonyms(name)
            for syn in learned_syns:
                if syn.lower() == failed_lower or failed_lower in syn.lower():
                    suggestions.append(name)
                    break
        
        # Fallback: partial match on name
        if not suggestions:
            for name in available_names:
                if failed_lower in name.lower() or name.lower() in failed_lower:
                    suggestions.append(name)
        
        return suggestions[:5]  # Top 5 suggestions
    
    def get_top_failed_lookups(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most common failed lookups."""
        sorted_failures = sorted(
            self.failed_lookups.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_failures[:limit]
    
    def get_query_success_rate(self) -> float:
        """Calculate overall query success rate."""
        if not self.query_history:
            return 0.0
        
        successful = sum(1 for q in self.query_history if q["success"])
        return successful / len(self.query_history)
    
    def get_learning_stats(self) -> Dict:
        """Get learning statistics."""
        return {
            "total_queries": len(self.query_history),
            "success_rate": self.get_query_success_rate(),
            "learned_synonyms_count": sum(len(syns) for syns in self.learned_synonyms.values()),
            "unique_failed_lookups": len(self.failed_lookups),
            "top_failures": self.get_top_failed_lookups(5)
        }
    
    def export_learned_synonyms(self) -> str:
        """Export learned synonyms as JSON for persistence."""
        return json.dumps(self.learned_synonyms, indent=2)
    
    def import_learned_synonyms(self, json_str: str):
        """Import learned synonyms from JSON."""
        try:
            imported = json.loads(json_str)
            for name, synonyms in imported.items():
                self.learned_synonyms[name].extend(synonyms)
                # Remove duplicates
                self.learned_synonyms[name] = list(set(self.learned_synonyms[name]))
        except Exception as e:
            logger.error(f"Failed to import learned synonyms: {e}")


def get_query_learner() -> QueryLearner:
    """Get or create the singleton QueryLearner instance."""
    global _query_learner
    if _query_learner is None:
        _query_learner = QueryLearner()
    return _query_learner
