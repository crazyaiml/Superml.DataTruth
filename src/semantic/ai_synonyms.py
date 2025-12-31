"""
AI Synonym Engine - Phase 2: Embedding-based synonym matching with auto-learning

This module provides intelligent synonym suggestions using semantic similarity
and learns from user corrections to improve over time.
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from sentence_transformers import SentenceTransformer
import numpy as np
from threading import Lock
import logging

logger = logging.getLogger(__name__)


@dataclass
class SynonymSuggestion:
    """A suggested synonym with confidence score"""
    term: str
    confidence: float
    source: str  # 'ai_learned', 'official', 'user_feedback'
    feedback_count: int = 0
    last_used: Optional[datetime] = None


@dataclass
class FeedbackEntry:
    """User feedback on synonym correctness"""
    user_query: str
    suggested_term: str
    actual_term: str  # What user actually meant
    user_id: str
    timestamp: datetime
    confirmed: bool  # True if suggestion was correct, False otherwise


class AISynonymEngine:
    """
    AI-powered synonym engine using sentence transformers for semantic matching.
    
    Features:
    - Embedding-based similarity matching
    - Learning from user corrections
    - Auto-promotion of frequently confirmed synonyms
    - Confidence scoring
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
        
        # Load sentence transformer model
        logger.info("Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
        
        # Storage for learned synonyms
        self.learned_synonyms: Dict[str, List[SynonymSuggestion]] = defaultdict(list)
        
        # Feedback storage
        self.feedback_history: List[FeedbackEntry] = []
        
        # Precomputed embeddings cache
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
        # Configuration
        self.confidence_threshold = 0.75  # Minimum confidence for suggestions
        self.promotion_threshold = 5  # Confirmations needed for auto-promotion
        self.max_suggestions = 5  # Max number of suggestions to return
        
        # Official synonym embeddings (will be loaded from semantic layer)
        self.official_embeddings: Dict[str, np.ndarray] = {}
        
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text, using cache if available"""
        if text not in self.embedding_cache:
            self.embedding_cache[text] = self.model.encode(text, convert_to_numpy=True)
        return self.embedding_cache[text]
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        emb1 = self._get_embedding(text1.lower())
        emb2 = self._get_embedding(text2.lower())
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def load_official_synonyms(self, metric_name: str, synonyms: List[str]):
        """
        Precompute embeddings for official synonyms
        
        Args:
            metric_name: Name of the metric
            synonyms: List of official synonyms for the metric
        """
        for synonym in synonyms:
            key = f"{metric_name}:{synonym}"
            if key not in self.official_embeddings:
                self.official_embeddings[key] = self._get_embedding(synonym.lower())
                
        logger.info(f"Loaded {len(synonyms)} official synonyms for {metric_name}")
    
    def suggest_synonyms(
        self,
        user_input: str,
        available_terms: List[str],
        official_synonyms: Optional[Dict[str, List[str]]] = None
    ) -> List[Tuple[str, SynonymSuggestion]]:
        """
        Suggest matching terms based on semantic similarity
        
        Args:
            user_input: User's natural language input
            available_terms: List of official terms (metrics, dimensions, etc.)
            official_synonyms: Map of term -> official synonyms
            
        Returns:
            List of (term, suggestion) tuples sorted by confidence
        """
        suggestions = []
        user_embedding = self._get_embedding(user_input.lower())
        
        # Check against official terms and their synonyms
        for term in available_terms:
            # Direct term similarity
            term_similarity = self._compute_similarity(user_input, term)
            
            if term_similarity >= self.confidence_threshold:
                suggestions.append((
                    term,
                    SynonymSuggestion(
                        term=user_input,
                        confidence=term_similarity,
                        source='official',
                        feedback_count=0
                    )
                ))
            
            # Check official synonyms
            if official_synonyms and term in official_synonyms:
                for synonym in official_synonyms[term]:
                    syn_similarity = self._compute_similarity(user_input, synonym)
                    if syn_similarity >= self.confidence_threshold:
                        suggestions.append((
                            term,
                            SynonymSuggestion(
                                term=user_input,
                                confidence=syn_similarity,
                                source='official',
                                feedback_count=0
                            )
                        ))
            
            # Check learned synonyms
            if term in self.learned_synonyms:
                for learned in self.learned_synonyms[term]:
                    learned_similarity = self._compute_similarity(user_input, learned.term)
                    if learned_similarity >= self.confidence_threshold:
                        # Boost confidence based on feedback count
                        boosted_confidence = min(
                            learned_similarity + (learned.feedback_count * 0.02),
                            1.0
                        )
                        suggestions.append((
                            term,
                            SynonymSuggestion(
                                term=learned.term,
                                confidence=boosted_confidence,
                                source='ai_learned',
                                feedback_count=learned.feedback_count,
                                last_used=learned.last_used
                            )
                        ))
        
        # Sort by confidence and return top suggestions
        suggestions.sort(key=lambda x: x[1].confidence, reverse=True)
        return suggestions[:self.max_suggestions]
    
    def learn_from_correction(
        self,
        user_query: str,
        suggested_term: str,
        actual_term: str,
        user_id: str,
        confirmed: bool = False
    ):
        """
        Learn from user feedback
        
        Args:
            user_query: Original user input
            suggested_term: What was suggested (can be None if no suggestion)
            actual_term: What the user actually meant
            user_id: ID of the user providing feedback
            confirmed: True if suggestion was correct, False if it was wrong
        """
        # Record feedback
        feedback = FeedbackEntry(
            user_query=user_query,
            suggested_term=suggested_term or "",
            actual_term=actual_term,
            user_id=user_id,
            timestamp=datetime.now(),
            confirmed=confirmed
        )
        self.feedback_history.append(feedback)
        
        # If user corrected our suggestion, learn from it
        if not confirmed and actual_term:
            # Find or create learned synonym entry
            existing = None
            for learned in self.learned_synonyms[actual_term]:
                if learned.term.lower() == user_query.lower():
                    existing = learned
                    break
            
            if existing:
                existing.feedback_count += 1
                existing.last_used = datetime.now()
            else:
                # Add new learned synonym
                self.learned_synonyms[actual_term].append(
                    SynonymSuggestion(
                        term=user_query,
                        confidence=self._compute_similarity(user_query, actual_term),
                        source='user_feedback',
                        feedback_count=1,
                        last_used=datetime.now()
                    )
                )
            
            # Check for auto-promotion
            if existing and existing.feedback_count >= self.promotion_threshold:
                self._promote_to_official_synonym(actual_term, user_query)
        
        # If user confirmed our suggestion, increase its confidence
        elif confirmed and suggested_term:
            for learned in self.learned_synonyms.get(actual_term, []):
                if learned.term.lower() == user_query.lower():
                    learned.feedback_count += 1
                    learned.last_used = datetime.now()
                    
                    # Check for auto-promotion
                    if learned.feedback_count >= self.promotion_threshold:
                        self._promote_to_official_synonym(actual_term, user_query)
                    break
        
        logger.info(
            f"Learned from feedback: query='{user_query}', "
            f"suggested='{suggested_term}', actual='{actual_term}', "
            f"confirmed={confirmed}"
        )
    
    def _promote_to_official_synonym(self, term: str, synonym: str):
        """
        Promote a learned synonym to official status
        
        This would typically update the semantic layer configuration,
        but for now we just mark it internally.
        """
        logger.info(
            f"🎓 Auto-promoting synonym: '{synonym}' -> '{term}' "
            f"(confirmed {self.promotion_threshold}+ times)"
        )
        
        # Update source to indicate promotion
        for learned in self.learned_synonyms[term]:
            if learned.term.lower() == synonym.lower():
                learned.source = 'ai_learned_promoted'
                break
    
    def get_feedback_summary(self, term: Optional[str] = None) -> Dict:
        """
        Get summary of feedback for a specific term or all terms
        
        Args:
            term: Specific term to get feedback for (None for all)
            
        Returns:
            Dictionary with feedback statistics
        """
        if term:
            relevant_feedback = [
                f for f in self.feedback_history
                if f.actual_term == term
            ]
        else:
            relevant_feedback = self.feedback_history
        
        total = len(relevant_feedback)
        confirmed = sum(1 for f in relevant_feedback if f.confirmed)
        
        return {
            'total_feedback': total,
            'confirmed': confirmed,
            'correction_rate': (total - confirmed) / total if total > 0 else 0,
            'learned_synonyms': len(self.learned_synonyms.get(term, [])) if term else sum(
                len(syns) for syns in self.learned_synonyms.values()
            ),
            'recent_feedback': [
                {
                    'query': f.user_query,
                    'suggested': f.suggested_term,
                    'actual': f.actual_term,
                    'confirmed': f.confirmed,
                    'timestamp': f.timestamp.isoformat()
                }
                for f in sorted(relevant_feedback, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }
    
    def get_learned_synonyms(self, term: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Get all learned synonyms, optionally filtered by term
        
        Args:
            term: Specific term to get synonyms for (None for all)
            
        Returns:
            Dictionary mapping terms to their learned synonyms
        """
        if term:
            terms_to_return = {term: self.learned_synonyms.get(term, [])}
        else:
            terms_to_return = dict(self.learned_synonyms)
        
        result = {}
        for term_key, suggestions in terms_to_return.items():
            result[term_key] = [
                {
                    'synonym': s.term,
                    'confidence': s.confidence,
                    'source': s.source,
                    'feedback_count': s.feedback_count,
                    'last_used': s.last_used.isoformat() if s.last_used else None
                }
                for s in sorted(suggestions, key=lambda x: x.feedback_count, reverse=True)
            ]
        
        return result
    
    def clear_learned_synonyms(self, term: Optional[str] = None):
        """
        Clear learned synonyms for a term or all terms
        
        Args:
            term: Specific term to clear (None for all)
        """
        if term:
            if term in self.learned_synonyms:
                del self.learned_synonyms[term]
                logger.info(f"Cleared learned synonyms for {term}")
        else:
            self.learned_synonyms.clear()
            logger.info("Cleared all learned synonyms")
    
    def export_learned_synonyms(self) -> Dict:
        """
        Export learned synonyms in a format suitable for adding to semantic layer
        
        Returns:
            Dictionary with promotable synonyms
        """
        promotable = {}
        
        for term, suggestions in self.learned_synonyms.items():
            high_confidence = [
                s for s in suggestions
                if s.feedback_count >= self.promotion_threshold
            ]
            
            if high_confidence:
                promotable[term] = [
                    {
                        'synonym': s.term,
                        'confidence': s.confidence,
                        'feedback_count': s.feedback_count,
                        'recommended_action': 'add_to_official'
                    }
                    for s in high_confidence
                ]
        
        return promotable


# Singleton instance
_engine = None

def get_synonym_engine() -> AISynonymEngine:
    """Get the singleton AISynonymEngine instance"""
    global _engine
    if _engine is None:
        _engine = AISynonymEngine()
    return _engine
