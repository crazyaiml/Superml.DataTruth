"""
Insight Learning and Feedback Module

Tracks user interactions with insights to improve ranking and relevance.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class InsightAction(str, Enum):
    """User actions on insights."""
    VIEWED = "viewed"
    DISMISSED = "dismissed"
    ACTED_ON = "acted_on"
    SHARED = "shared"
    SAVED = "saved"


class InsightFeedback(BaseModel):
    """User feedback on an insight."""
    insight_id: str = Field(description="Insight identifier")
    user_id: str = Field(description="User who provided feedback")
    action: InsightAction = Field(description="Action taken")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class InsightScore(BaseModel):
    """Scored insight with impact and relevance."""
    insight_id: str = Field(description="Insight identifier")
    base_score: float = Field(description="Base score from confidence and severity")
    user_engagement_score: float = Field(description="Score based on user interactions")
    recency_score: float = Field(description="Score based on how recent the insight is")
    final_score: float = Field(description="Combined final score")
    impact_level: str = Field(description="high, medium, or low")


class InsightLearner:
    """Learns from user interactions to improve insight ranking."""
    
    def __init__(self):
        # In-memory storage (replace with DB in production)
        self.feedback_history: List[InsightFeedback] = []
        self.insight_scores: Dict[str, float] = {}
    
    def record_feedback(self, feedback: InsightFeedback):
        """Record user feedback on an insight."""
        self.feedback_history.append(feedback)
        
        # Update insight score
        insight_id = feedback.insight_id
        current_score = self.insight_scores.get(insight_id, 0.5)
        
        # Adjust score based on action
        action_weights = {
            InsightAction.VIEWED: 0.02,
            InsightAction.DISMISSED: -0.1,
            InsightAction.ACTED_ON: 0.3,
            InsightAction.SHARED: 0.2,
            InsightAction.SAVED: 0.15
        }
        
        adjustment = action_weights.get(feedback.action, 0)
        new_score = max(0.0, min(1.0, current_score + adjustment))
        self.insight_scores[insight_id] = new_score
    
    def calculate_impact_score(
        self,
        insight_id: str,
        base_confidence: float,
        severity: str,
        age_hours: float
    ) -> InsightScore:
        """
        Calculate comprehensive impact score for an insight.
        
        Args:
            insight_id: Insight identifier
            base_confidence: Confidence from analysis (0-1)
            severity: Severity level
            age_hours: How old the insight is in hours
            
        Returns:
            InsightScore with detailed scoring
        """
        # Base score from confidence and severity
        severity_weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "info": 0.2
        }
        severity_weight = severity_weights.get(severity.lower(), 0.5)
        base_score = (base_confidence * 0.6 + severity_weight * 0.4)
        
        # User engagement score from historical feedback
        user_engagement_score = self.insight_scores.get(insight_id, 0.5)
        
        # Recency score (decay over time)
        # Fresh insights (< 1 hour) get full score, decay to 0.5 over 7 days
        max_age_hours = 168  # 7 days
        recency_score = max(0.5, 1.0 - (age_hours / max_age_hours) * 0.5)
        
        # Combined final score (weighted average)
        final_score = (
            base_score * 0.4 +
            user_engagement_score * 0.3 +
            recency_score * 0.3
        )
        
        # Determine impact level
        if final_score >= 0.8:
            impact_level = "high"
        elif final_score >= 0.6:
            impact_level = "medium"
        else:
            impact_level = "low"
        
        return InsightScore(
            insight_id=insight_id,
            base_score=base_score,
            user_engagement_score=user_engagement_score,
            recency_score=recency_score,
            final_score=final_score,
            impact_level=impact_level
        )
    
    def get_feedback_stats(self, insight_id: str) -> Dict[str, Any]:
        """Get feedback statistics for an insight."""
        feedback_list = [f for f in self.feedback_history if f.insight_id == insight_id]
        
        if not feedback_list:
            return {"total": 0}
        
        stats = {
            "total": len(feedback_list),
            "viewed": sum(1 for f in feedback_list if f.action == InsightAction.VIEWED),
            "dismissed": sum(1 for f in feedback_list if f.action == InsightAction.DISMISSED),
            "acted_on": sum(1 for f in feedback_list if f.action == InsightAction.ACTED_ON),
            "shared": sum(1 for f in feedback_list if f.action == InsightAction.SHARED),
            "saved": sum(1 for f in feedback_list if f.action == InsightAction.SAVED),
            "engagement_rate": sum(
                1 for f in feedback_list 
                if f.action in [InsightAction.ACTED_ON, InsightAction.SHARED, InsightAction.SAVED]
            ) / len(feedback_list)
        }
        
        return stats


# Singleton
_insight_learner = None

def get_insight_learner() -> InsightLearner:
    """Get singleton InsightLearner instance."""
    global _insight_learner
    if _insight_learner is None:
        _insight_learner = InsightLearner()
    return _insight_learner
