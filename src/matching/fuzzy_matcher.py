"""
Fuzzy Matcher - Phase 3: Typo-tolerant string matching

This module provides fuzzy string matching to handle typos, abbreviations,
and variations in user input.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import logging
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a fuzzy match"""
    matched_value: str
    original_value: str
    score: float  # 0.0 to 1.0
    match_type: str  # 'exact', 'fuzzy', 'phonetic', 'abbreviation'
    metadata: Dict = None


class FuzzyMatcher:
    """
    Fuzzy string matching with multiple algorithms.
    
    Features:
    - Levenshtein distance matching
    - Phonetic matching (Soundex/Metaphone)
    - Abbreviation expansion
    - Case-insensitive matching
    - Configurable thresholds
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
        
        # Configuration
        self.fuzzy_threshold = 0.75  # Minimum similarity for fuzzy match
        self.max_suggestions = 5
        
        # Common abbreviations
        self.abbreviations = {
            'rev': ['revenue', 'revenues'],
            'prof': ['profit', 'profits'],
            'cust': ['customer', 'customers'],
            'qty': ['quantity'],
            'amt': ['amount'],
            'avg': ['average'],
            'min': ['minimum'],
            'max': ['maximum'],
            'tot': ['total'],
            'pct': ['percent', 'percentage'],
            'yr': ['year'],
            'mo': ['month'],
            'wk': ['week'],
            'qtr': ['quarter'],
        }
        
        logger.info("Fuzzy Matcher initialized")
    
    def find_matches(
        self,
        query: str,
        candidates: List[str],
        threshold: Optional[float] = None,
        max_results: Optional[int] = None
    ) -> List[MatchResult]:
        """
        Find fuzzy matches for query string
        
        Args:
            query: User input to match
            candidates: List of valid values to match against
            threshold: Minimum similarity score (0.0 to 1.0)
            max_results: Maximum number of results
            
        Returns:
            List of MatchResult objects sorted by score
        """
        if threshold is None:
            threshold = self.fuzzy_threshold
        if max_results is None:
            max_results = self.max_suggestions
        
        query_normalized = self._normalize(query)
        matches = []
        
        for candidate in candidates:
            candidate_normalized = self._normalize(candidate)
            
            # Try exact match first
            if query_normalized == candidate_normalized:
                matches.append(MatchResult(
                    matched_value=candidate,
                    original_value=query,
                    score=1.0,
                    match_type='exact'
                ))
                continue
            
            # Try abbreviation expansion
            abbrev_score = self._check_abbreviation(query_normalized, candidate_normalized)
            if abbrev_score >= threshold:
                matches.append(MatchResult(
                    matched_value=candidate,
                    original_value=query,
                    score=abbrev_score,
                    match_type='abbreviation'
                ))
                continue
            
            # Try fuzzy string matching
            fuzzy_score = self._calculate_similarity(query_normalized, candidate_normalized)
            if fuzzy_score >= threshold:
                matches.append(MatchResult(
                    matched_value=candidate,
                    original_value=query,
                    score=fuzzy_score,
                    match_type='fuzzy'
                ))
                continue
            
            # Try phonetic matching (for common misspellings)
            phonetic_score = self._phonetic_similarity(query_normalized, candidate_normalized)
            if phonetic_score >= threshold:
                matches.append(MatchResult(
                    matched_value=candidate,
                    original_value=query,
                    score=phonetic_score,
                    match_type='phonetic'
                ))
        
        # Sort by score (descending) and return top results
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:max_results]
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using SequenceMatcher"""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _check_abbreviation(self, query: str, candidate: str) -> float:
        """Check if query is an abbreviation of candidate"""
        # Check in abbreviations dictionary
        if query in self.abbreviations:
            expansions = self.abbreviations[query]
            for expansion in expansions:
                if candidate.startswith(expansion) or expansion.startswith(candidate):
                    return 0.9  # High confidence for known abbreviations
        
        # Check if query matches first letters
        if len(query) <= len(candidate):
            candidate_words = candidate.split()
            query_chars = query.replace(' ', '')
            
            # Check acronym (first letters of each word)
            if len(candidate_words) >= len(query_chars):
                acronym = ''.join(word[0] for word in candidate_words[:len(query_chars)])
                if query_chars == acronym:
                    return 0.85
            
            # Check prefix match
            if candidate.startswith(query):
                return 0.8
        
        return 0.0
    
    def _phonetic_similarity(self, str1: str, str2: str) -> float:
        """
        Simplified phonetic matching
        (In production, use libraries like phonetics or jellyfish)
        """
        # Convert to simplified phonetic representation
        phonetic1 = self._to_phonetic(str1)
        phonetic2 = self._to_phonetic(str2)
        
        # Calculate similarity of phonetic representations
        similarity = self._calculate_similarity(phonetic1, phonetic2)
        
        # Lower confidence for phonetic matches
        return similarity * 0.8 if similarity > 0.7 else 0.0
    
    def _to_phonetic(self, text: str) -> str:
        """
        Convert to simplified phonetic representation
        (Simplified version - production would use Soundex/Metaphone)
        """
        # Remove vowels except first character
        if not text:
            return ""
        
        result = text[0]
        for char in text[1:]:
            if char not in 'aeiou':
                result += char
        
        return result
    
    def add_abbreviation(self, abbrev: str, expansions: List[str]):
        """Add custom abbreviation"""
        abbrev = abbrev.lower()
        self.abbreviations[abbrev] = [e.lower() for e in expansions]
        logger.info(f"Added abbreviation: {abbrev} -> {expansions}")
    
    def match_dimension_value(
        self,
        user_input: str,
        dimension_values: List[str],
        threshold: float = 0.7
    ) -> Optional[MatchResult]:
        """
        Match user input to a dimension value with typo tolerance
        
        Example:
            user_input = "Caifornia"  (typo)
            dimension_values = ["California", "Texas", "Florida"]
            returns: MatchResult(matched_value="California", score=0.89)
        """
        matches = self.find_matches(user_input, dimension_values, threshold, max_results=1)
        return matches[0] if matches else None
    
    def bulk_match(
        self,
        queries: List[str],
        candidates: List[str],
        threshold: float = 0.75
    ) -> Dict[str, List[MatchResult]]:
        """
        Match multiple queries efficiently
        
        Returns:
            Dictionary mapping each query to its matches
        """
        results = {}
        for query in queries:
            matches = self.find_matches(query, candidates, threshold)
            if matches:
                results[query] = matches
        
        return results
    
    def suggest_corrections(
        self,
        text: str,
        valid_terms: List[str]
    ) -> List[Tuple[str, str, float]]:
        """
        Suggest corrections for potentially misspelled terms
        
        Returns:
            List of (original, suggestion, confidence) tuples
        """
        words = text.split()
        suggestions = []
        
        for word in words:
            matches = self.find_matches(word, valid_terms, threshold=0.6, max_results=1)
            if matches and matches[0].score < 1.0:  # Not exact match
                suggestions.append((
                    word,
                    matches[0].matched_value,
                    matches[0].score
                ))
        
        return suggestions


# Singleton instance
_matcher = None

def get_fuzzy_matcher() -> FuzzyMatcher:
    """Get the singleton FuzzyMatcher instance"""
    global _matcher
    if _matcher is None:
        _matcher = FuzzyMatcher()
    return _matcher
