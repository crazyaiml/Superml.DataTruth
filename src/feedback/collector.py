"""
Feedback Collector - Phase 2: User feedback collection and processing

This module collects user feedback on query results, synonym suggestions,
and other AI features to improve the system over time.
"""

from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback users can provide"""
    QUERY_CORRECT = "query_correct"  # Query result was correct
    QUERY_WRONG = "query_wrong"  # Query result was wrong
    SYNONYM_CORRECT = "synonym_correct"  # Suggested synonym was correct
    SYNONYM_WRONG = "synonym_wrong"  # Suggested synonym was wrong
    MISSING_SYNONYM = "missing_synonym"  # User taught us a new synonym
    METRIC_SUGGESTION = "metric_suggestion"  # User wants a new metric
    DIMENSION_SUGGESTION = "dimension_suggestion"  # User wants a new dimension
    GENERAL_FEEDBACK = "general_feedback"  # General comment


@dataclass
class FeedbackEntry:
    """A single feedback entry"""
    id: str
    user_id: str
    username: str
    feedback_type: FeedbackType
    timestamp: datetime
    
    # Query context
    original_query: Optional[str] = None
    generated_sql: Optional[str] = None
    intent: Optional[Dict] = None
    
    # Suggestion context
    suggested_term: Optional[str] = None
    actual_term: Optional[str] = None
    confidence_score: Optional[float] = None
    
    # User provided data
    comment: Optional[str] = None
    rating: Optional[int] = None  # 1-5 stars
    metadata: Dict = field(default_factory=dict)
    
    # Processing status
    processed: bool = False
    applied_to_learning: bool = False


class FeedbackCollector:
    """
    Collects and manages user feedback for continuous improvement.
    
    Features:
    - Multiple feedback types
    - Persistent storage
    - Integration with AI synonym engine
    - Analytics and reporting
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, storage_path: str = "./feedback_data"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._storage_path = storage_path
                    cls._instance = instance
        return cls._instance
    
    def __init__(self, storage_path: str = "./feedback_data"):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # Use the storage_path from __new__ if available
        if hasattr(self, '_storage_path'):
            storage_path = self._storage_path
        
        # Setup storage
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self.feedback_entries: List[FeedbackEntry] = []
        
        # Load existing feedback
        self._load_feedback()
        
        # Counter for generating IDs
        self.feedback_counter = len(self.feedback_entries)
        
        logger.info(f"Feedback collector initialized with {len(self.feedback_entries)} entries")
    
    def _generate_id(self) -> str:
        """Generate unique feedback ID"""
        self.feedback_counter += 1
        return f"fb_{datetime.now().strftime('%Y%m%d')}_{self.feedback_counter:06d}"
    
    def _load_feedback(self):
        """Load feedback from persistent storage"""
        feedback_file = self.storage_path / "feedback.jsonl"
        if feedback_file.exists():
            try:
                with open(feedback_file, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        entry = FeedbackEntry(
                            id=data['id'],
                            user_id=data['user_id'],
                            username=data['username'],
                            feedback_type=FeedbackType(data['feedback_type']),
                            timestamp=datetime.fromisoformat(data['timestamp']),
                            original_query=data.get('original_query'),
                            generated_sql=data.get('generated_sql'),
                            intent=data.get('intent'),
                            suggested_term=data.get('suggested_term'),
                            actual_term=data.get('actual_term'),
                            confidence_score=data.get('confidence_score'),
                            comment=data.get('comment'),
                            rating=data.get('rating'),
                            metadata=data.get('metadata', {}),
                            processed=data.get('processed', False),
                            applied_to_learning=data.get('applied_to_learning', False)
                        )
                        self.feedback_entries.append(entry)
                logger.info(f"Loaded {len(self.feedback_entries)} feedback entries")
            except Exception as e:
                logger.error(f"Error loading feedback: {e}")
    
    def _save_feedback(self, entry: FeedbackEntry):
        """Save feedback entry to persistent storage"""
        feedback_file = self.storage_path / "feedback.jsonl"
        try:
            with open(feedback_file, 'a') as f:
                data = {
                    'id': entry.id,
                    'user_id': entry.user_id,
                    'username': entry.username,
                    'feedback_type': entry.feedback_type.value,
                    'timestamp': entry.timestamp.isoformat(),
                    'original_query': entry.original_query,
                    'generated_sql': entry.generated_sql,
                    'intent': entry.intent,
                    'suggested_term': entry.suggested_term,
                    'actual_term': entry.actual_term,
                    'confidence_score': entry.confidence_score,
                    'comment': entry.comment,
                    'rating': entry.rating,
                    'metadata': entry.metadata,
                    'processed': entry.processed,
                    'applied_to_learning': entry.applied_to_learning
                }
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    
    def record_feedback(
        self,
        user_id: str,
        username: str,
        feedback_type: FeedbackType,
        original_query: Optional[str] = None,
        generated_sql: Optional[str] = None,
        intent: Optional[Dict] = None,
        suggested_term: Optional[str] = None,
        actual_term: Optional[str] = None,
        confidence_score: Optional[float] = None,
        comment: Optional[str] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> FeedbackEntry:
        """
        Record user feedback
        
        Args:
            user_id: ID of the user providing feedback
            username: Username of the user
            feedback_type: Type of feedback
            original_query: Original natural language query
            generated_sql: Generated SQL (if applicable)
            intent: Extracted intent (if applicable)
            suggested_term: Term that was suggested
            actual_term: Term that user actually meant
            confidence_score: Confidence score of suggestion
            comment: User's comment
            rating: 1-5 star rating
            metadata: Additional metadata
            
        Returns:
            Created FeedbackEntry
        """
        entry = FeedbackEntry(
            id=self._generate_id(),
            user_id=user_id,
            username=username,
            feedback_type=feedback_type,
            timestamp=datetime.now(),
            original_query=original_query,
            generated_sql=generated_sql,
            intent=intent,
            suggested_term=suggested_term,
            actual_term=actual_term,
            confidence_score=confidence_score,
            comment=comment,
            rating=rating,
            metadata=metadata or {}
        )
        
        self.feedback_entries.append(entry)
        self._save_feedback(entry)
        
        logger.info(
            f"Recorded {feedback_type.value} feedback from {username}: "
            f"query='{original_query}', suggested='{suggested_term}', actual='{actual_term}'"
        )
        
        return entry
    
    def get_feedback(
        self,
        feedback_type: Optional[FeedbackType] = None,
        user_id: Optional[str] = None,
        processed: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[FeedbackEntry]:
        """
        Get feedback entries matching criteria
        
        Args:
            feedback_type: Filter by feedback type
            user_id: Filter by user ID
            processed: Filter by processed status
            limit: Maximum number of entries to return
            
        Returns:
            List of matching FeedbackEntry objects
        """
        results = self.feedback_entries
        
        if feedback_type:
            results = [e for e in results if e.feedback_type == feedback_type]
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        
        if processed is not None:
            results = [e for e in results if e.processed == processed]
        
        # Sort by timestamp (newest first)
        results = sorted(results, key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def mark_processed(self, feedback_id: str, applied_to_learning: bool = False):
        """
        Mark feedback as processed
        
        Args:
            feedback_id: ID of the feedback entry
            applied_to_learning: Whether the feedback was applied to learning
        """
        for entry in self.feedback_entries:
            if entry.id == feedback_id:
                entry.processed = True
                entry.applied_to_learning = applied_to_learning
                logger.info(f"Marked feedback {feedback_id} as processed")
                break
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about collected feedback
        
        Returns:
            Dictionary with feedback statistics
        """
        total = len(self.feedback_entries)
        if total == 0:
            return {
                'total': 0,
                'by_type': {},
                'processed': 0,
                'applied_to_learning': 0,
                'avg_rating': None
            }
        
        by_type = {}
        for entry in self.feedback_entries:
            type_name = entry.feedback_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        processed = sum(1 for e in self.feedback_entries if e.processed)
        applied_to_learning = sum(1 for e in self.feedback_entries if e.applied_to_learning)
        
        ratings = [e.rating for e in self.feedback_entries if e.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        return {
            'total': total,
            'by_type': by_type,
            'processed': processed,
            'unprocessed': total - processed,
            'applied_to_learning': applied_to_learning,
            'avg_rating': round(avg_rating, 2) if avg_rating else None,
            'total_ratings': len(ratings)
        }
    
    def get_recent_feedback(self, limit: int = 20) -> List[Dict]:
        """
        Get recent feedback entries as dictionaries
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of feedback dictionaries
        """
        recent = sorted(
            self.feedback_entries,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
        
        return [
            {
                'id': e.id,
                'user_id': e.user_id,
                'username': e.username,
                'type': e.feedback_type.value,
                'timestamp': e.timestamp.isoformat(),
                'original_query': e.original_query,
                'suggested_term': e.suggested_term,
                'actual_term': e.actual_term,
                'confidence_score': e.confidence_score,
                'comment': e.comment,
                'rating': e.rating,
                'processed': e.processed
            }
            for e in recent
        ]
    
    def process_synonym_feedback(self, synonym_engine):
        """
        Process pending synonym feedback and apply to learning
        
        Args:
            synonym_engine: AISynonymEngine instance to apply feedback to
        """
        # Get unprocessed synonym feedback
        synonym_feedback = [
            e for e in self.feedback_entries
            if e.feedback_type in [
                FeedbackType.SYNONYM_CORRECT,
                FeedbackType.SYNONYM_WRONG,
                FeedbackType.MISSING_SYNONYM
            ] and not e.applied_to_learning
        ]
        
        processed_count = 0
        for entry in synonym_feedback:
            if entry.original_query and entry.actual_term:
                # Determine if this was a confirmation or correction
                confirmed = entry.feedback_type == FeedbackType.SYNONYM_CORRECT
                
                # Apply to synonym engine
                synonym_engine.learn_from_correction(
                    user_query=entry.original_query,
                    suggested_term=entry.suggested_term or "",
                    actual_term=entry.actual_term,
                    user_id=entry.user_id,
                    confirmed=confirmed
                )
                
                # Mark as processed
                self.mark_processed(entry.id, applied_to_learning=True)
                processed_count += 1
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} synonym feedback entries")
        
        return processed_count


# Singleton instance
_collector = None

def get_feedback_collector(storage_path: str = "./feedback_data") -> FeedbackCollector:
    """Get the singleton FeedbackCollector instance"""
    global _collector
    if _collector is None:
        _collector = FeedbackCollector(storage_path)
    return _collector
