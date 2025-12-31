"""
Feedback Collector

Collects user feedback to improve semantic layer.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Singleton instance
_feedback_collector = None


class FeedbackCollector:
    """
    Collects and processes user feedback for learning.
    """
    
    def __init__(self):
        """Initialize feedback collector."""
        self.feedback_history: List[Dict] = []
    
    def record_feedback(
        self,
        query_id: str,
        user_query: str,
        was_helpful: bool,
        corrected_metric: Optional[str] = None,
        corrected_dimensions: Optional[List[str]] = None,
        user_comment: Optional[str] = None
    ):
        """
        Record user feedback on a query.
        
        Args:
            query_id: Unique query identifier
            user_query: Original user query
            was_helpful: Whether the result was helpful
            corrected_metric: User's correction for metric (if any)
            corrected_dimensions: User's corrections for dimensions
            user_comment: Optional user comment
        """
        feedback = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_id": query_id,
            "user_query": user_query,
            "was_helpful": was_helpful,
            "corrected_metric": corrected_metric,
            "corrected_dimensions": corrected_dimensions or [],
            "user_comment": user_comment
        }
        
        self.feedback_history.append(feedback)
        logger.info(f"Recorded feedback for query: {query_id}, helpful: {was_helpful}")
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics."""
        if not self.feedback_history:
            return {
                "total_feedback": 0,
                "helpful_rate": 0.0,
                "corrections_received": 0
            }
        
        total = len(self.feedback_history)
        helpful = sum(1 for f in self.feedback_history if f["was_helpful"])
        corrections = sum(
            1 for f in self.feedback_history
            if f["corrected_metric"] or f["corrected_dimensions"]
        )
        
        return {
            "total_feedback": total,
            "helpful_rate": helpful / total if total > 0 else 0.0,
            "corrections_received": corrections
        }


def get_feedback_collector() -> FeedbackCollector:
    """Get or create the singleton FeedbackCollector instance."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector
