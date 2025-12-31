"""
Matching module for fuzzy string matching and entity resolution
"""

from .fuzzy_matcher import FuzzyMatcher, MatchResult, get_fuzzy_matcher
from .entity_matcher import EntityMatcher, EntityMatch, get_entity_matcher

__all__ = [
    'FuzzyMatcher',
    'MatchResult',
    'get_fuzzy_matcher',
    'EntityMatcher',
    'EntityMatch',
    'get_entity_matcher'
]
