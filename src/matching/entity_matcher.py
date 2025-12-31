"""
Entity Matcher - Phase 3: Multi-source entity resolution

This module matches and reconciles entities across multiple data sources.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from threading import Lock

from .fuzzy_matcher import FuzzyMatcher, get_fuzzy_matcher

logger = logging.getLogger(__name__)


class MatchStrategy(Enum):
    """Strategy for entity matching"""
    EXACT = "exact"  # Exact match on key fields
    FUZZY = "fuzzy"  # Fuzzy match with similarity threshold
    COMPOSITE = "composite"  # Match on multiple fields
    HIERARCHICAL = "hierarchical"  # Match with parent-child relationships


class ConflictResolution(Enum):
    """Strategy for resolving conflicts in matched entities"""
    MOST_RECENT = "most_recent"  # Use most recent data
    HIGHEST_QUALITY = "highest_quality"  # Use highest quality source
    MERGE = "merge"  # Merge data from all sources
    MANUAL = "manual"  # Flag for manual review


@dataclass
class EntityMatch:
    """Result of matching two entities"""
    source1_id: str
    source2_id: str
    source1_name: str
    source2_name: str
    confidence: float  # 0.0 to 1.0
    matched_fields: List[str]
    conflicting_fields: List[str] = field(default_factory=list)
    match_strategy: str = "fuzzy"
    metadata: Dict = field(default_factory=dict)


@dataclass
class ResolvedEntity:
    """Entity resolved from multiple sources"""
    entity_id: str
    entity_type: str
    canonical_data: Dict
    source_ids: Dict[str, str]  # source_name -> source_id
    confidence: float
    conflicts: List[Dict] = field(default_factory=list)
    resolved_at: Optional[datetime] = None


class EntityMatcher:
    """
    Match and reconcile entities across multiple data sources.
    
    Features:
    - Multi-key matching
    - Confidence scoring
    - Conflict detection and resolution
    - Provenance tracking
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
        self.fuzzy_matcher = get_fuzzy_matcher()
        
        # Match cache
        self.match_cache: Dict[str, List[EntityMatch]] = {}
        
        # Quality scores by source
        self.source_quality: Dict[str, float] = {}
        
        logger.info("Entity Matcher initialized")
    
    def match_entities(
        self,
        source1_data: List[Dict],
        source2_data: List[Dict],
        key_fields: List[str],
        strategy: MatchStrategy = MatchStrategy.FUZZY,
        threshold: float = 0.75
    ) -> List[EntityMatch]:
        """
        Match entities from two data sources
        
        Args:
            source1_data: List of entities from source 1
            source2_data: List of entities from source 2
            key_fields: Fields to use for matching
            strategy: Matching strategy
            threshold: Minimum confidence for fuzzy matching
            
        Returns:
            List of EntityMatch results
        """
        logger.info(f"Matching {len(source1_data)} entities from source1 with {len(source2_data)} from source2")
        
        matches = []
        
        for entity1 in source1_data:
            best_matches = self._find_best_matches(
                entity1,
                source2_data,
                key_fields,
                strategy,
                threshold
            )
            matches.extend(best_matches)
        
        # Cache results
        cache_key = self._generate_cache_key(key_fields, strategy, threshold)
        self.match_cache[cache_key] = matches
        
        logger.info(f"Found {len(matches)} matches")
        return matches
    
    def _find_best_matches(
        self,
        entity1: Dict,
        candidates: List[Dict],
        key_fields: List[str],
        strategy: MatchStrategy,
        threshold: float
    ) -> List[EntityMatch]:
        """Find best matching candidates for an entity"""
        matches = []
        
        for entity2 in candidates:
            match = self._match_pair(
                entity1,
                entity2,
                key_fields,
                strategy,
                threshold
            )
            
            if match and match.confidence >= threshold:
                matches.append(match)
        
        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        # Return top match only (1:1 matching)
        return matches[:1] if matches else []
    
    def _match_pair(
        self,
        entity1: Dict,
        entity2: Dict,
        key_fields: List[str],
        strategy: MatchStrategy,
        threshold: float
    ) -> Optional[EntityMatch]:
        """Match a pair of entities"""
        
        if strategy == MatchStrategy.EXACT:
            return self._exact_match(entity1, entity2, key_fields)
        elif strategy == MatchStrategy.FUZZY:
            return self._fuzzy_match(entity1, entity2, key_fields, threshold)
        elif strategy == MatchStrategy.COMPOSITE:
            return self._composite_match(entity1, entity2, key_fields, threshold)
        else:
            logger.warning(f"Strategy {strategy} not implemented, using fuzzy")
            return self._fuzzy_match(entity1, entity2, key_fields, threshold)
    
    def _exact_match(
        self,
        entity1: Dict,
        entity2: Dict,
        key_fields: List[str]
    ) -> Optional[EntityMatch]:
        """Exact match on key fields"""
        matched_fields = []
        
        for field in key_fields:
            val1 = entity1.get(field)
            val2 = entity2.get(field)
            
            if val1 and val2 and str(val1).lower() == str(val2).lower():
                matched_fields.append(field)
        
        if matched_fields:
            confidence = len(matched_fields) / len(key_fields)
            
            return EntityMatch(
                source1_id=entity1.get('id', 'unknown'),
                source2_id=entity2.get('id', 'unknown'),
                source1_name=self._get_entity_name(entity1),
                source2_name=self._get_entity_name(entity2),
                confidence=confidence,
                matched_fields=matched_fields,
                match_strategy="exact"
            )
        
        return None
    
    def _fuzzy_match(
        self,
        entity1: Dict,
        entity2: Dict,
        key_fields: List[str],
        threshold: float
    ) -> Optional[EntityMatch]:
        """Fuzzy match using similarity"""
        field_scores = []
        matched_fields = []
        
        for field in key_fields:
            val1 = entity1.get(field)
            val2 = entity2.get(field)
            
            if not val1 or not val2:
                continue
            
            # Use fuzzy matcher
            result = self.fuzzy_matcher.find_matches(
                query=str(val1),
                candidates=[str(val2)],
                threshold=threshold,
                max_results=1
            )
            
            if result:
                score = result[0].score
                field_scores.append(score)
                if score >= threshold:
                    matched_fields.append(field)
        
        if not field_scores:
            return None
        
        # Average confidence across all fields
        confidence = sum(field_scores) / len(field_scores)
        
        if confidence >= threshold:
            # Detect conflicts
            conflicting_fields = self._detect_conflicts(entity1, entity2, key_fields)
            
            return EntityMatch(
                source1_id=entity1.get('id', 'unknown'),
                source2_id=entity2.get('id', 'unknown'),
                source1_name=self._get_entity_name(entity1),
                source2_name=self._get_entity_name(entity2),
                confidence=confidence,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                match_strategy="fuzzy"
            )
        
        return None
    
    def _composite_match(
        self,
        entity1: Dict,
        entity2: Dict,
        key_fields: List[str],
        threshold: float
    ) -> Optional[EntityMatch]:
        """Match using weighted combination of fields"""
        # Assign weights to fields
        weights = {field: 1.0 / len(key_fields) for field in key_fields}
        
        # Special weighting for common fields
        if 'id' in key_fields:
            weights['id'] = 0.5
        if 'name' in key_fields:
            weights['name'] = 0.3
        
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        field_scores = {}
        matched_fields = []
        
        for field in key_fields:
            val1 = entity1.get(field)
            val2 = entity2.get(field)
            
            if not val1 or not val2:
                field_scores[field] = 0.0
                continue
            
            # Calculate similarity
            result = self.fuzzy_matcher.find_matches(
                query=str(val1),
                candidates=[str(val2)],
                threshold=0.5,  # Lower threshold for composite
                max_results=1
            )
            
            if result:
                score = result[0].score
                field_scores[field] = score * weights[field]
                if score >= threshold:
                    matched_fields.append(field)
            else:
                field_scores[field] = 0.0
        
        # Weighted confidence
        confidence = sum(field_scores.values())
        
        if confidence >= threshold:
            conflicting_fields = self._detect_conflicts(entity1, entity2, key_fields)
            
            return EntityMatch(
                source1_id=entity1.get('id', 'unknown'),
                source2_id=entity2.get('id', 'unknown'),
                source1_name=self._get_entity_name(entity1),
                source2_name=self._get_entity_name(entity2),
                confidence=confidence,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                match_strategy="composite",
                metadata={'field_scores': field_scores}
            )
        
        return None
    
    def _detect_conflicts(
        self,
        entity1: Dict,
        entity2: Dict,
        fields: List[str]
    ) -> List[str]:
        """Detect conflicting field values"""
        conflicts = []
        
        for field in fields:
            val1 = entity1.get(field)
            val2 = entity2.get(field)
            
            if val1 and val2 and str(val1).lower() != str(val2).lower():
                conflicts.append(field)
        
        return conflicts
    
    def resolve_entity(
        self,
        matches: List[EntityMatch],
        entity_data: Dict[str, Dict],
        strategy: ConflictResolution = ConflictResolution.HIGHEST_QUALITY
    ) -> ResolvedEntity:
        """
        Resolve conflicts and create canonical entity
        
        Args:
            matches: List of matches for this entity
            entity_data: Dictionary of source_name -> entity_data
            strategy: Conflict resolution strategy
            
        Returns:
            ResolvedEntity with canonical data
        """
        if not matches:
            raise ValueError("No matches provided for resolution")
        
        # Collect all sources
        source_ids = {}
        all_data = []
        
        for match in matches:
            source_ids[match.source1_name] = match.source1_id
            source_ids[match.source2_name] = match.source2_id
            
            if match.source1_name in entity_data:
                all_data.append((match.source1_name, entity_data[match.source1_name]))
            if match.source2_name in entity_data:
                all_data.append((match.source2_name, entity_data[match.source2_name]))
        
        # Resolve based on strategy
        if strategy == ConflictResolution.HIGHEST_QUALITY:
            canonical_data = self._resolve_by_quality(all_data)
        elif strategy == ConflictResolution.MERGE:
            canonical_data = self._resolve_by_merge(all_data)
        elif strategy == ConflictResolution.MOST_RECENT:
            canonical_data = self._resolve_by_recency(all_data)
        else:
            # Default to merge
            canonical_data = self._resolve_by_merge(all_data)
        
        # Calculate overall confidence
        confidence = sum(m.confidence for m in matches) / len(matches)
        
        # Collect conflicts
        conflicts = []
        for match in matches:
            if match.conflicting_fields:
                conflicts.append({
                    'fields': match.conflicting_fields,
                    'sources': [match.source1_name, match.source2_name]
                })
        
        return ResolvedEntity(
            entity_id=canonical_data.get('id', 'resolved_' + str(hash(str(source_ids)))),
            entity_type=canonical_data.get('type', 'unknown'),
            canonical_data=canonical_data,
            source_ids=source_ids,
            confidence=confidence,
            conflicts=conflicts,
            resolved_at=datetime.now()
        )
    
    def _resolve_by_quality(self, all_data: List[Tuple[str, Dict]]) -> Dict:
        """Resolve using highest quality source"""
        # Sort by source quality (highest first)
        sorted_data = sorted(
            all_data,
            key=lambda x: self.source_quality.get(x[0], 0.5),
            reverse=True
        )
        
        # Use highest quality source as base
        canonical = sorted_data[0][1].copy()
        
        return canonical
    
    def _resolve_by_merge(self, all_data: List[Tuple[str, Dict]]) -> Dict:
        """Merge data from all sources"""
        canonical = {}
        
        for source_name, data in all_data:
            for key, value in data.items():
                if key not in canonical and value is not None:
                    canonical[key] = value
        
        return canonical
    
    def _resolve_by_recency(self, all_data: List[Tuple[str, Dict]]) -> Dict:
        """Use most recent data"""
        # Assume data has 'updated_at' or 'created_at' field
        sorted_data = sorted(
            all_data,
            key=lambda x: x[1].get('updated_at', x[1].get('created_at', '')),
            reverse=True
        )
        
        return sorted_data[0][1].copy()
    
    def _get_entity_name(self, entity: Dict) -> str:
        """Extract entity name from data"""
        return entity.get('name', entity.get('id', 'unknown'))
    
    def _generate_cache_key(
        self,
        key_fields: List[str],
        strategy: MatchStrategy,
        threshold: float
    ) -> str:
        """Generate cache key for match results"""
        return f"{'-'.join(key_fields)}_{strategy.value}_{threshold}"
    
    def set_source_quality(self, source_name: str, quality_score: float):
        """Set quality score for a data source (0.0 to 1.0)"""
        if not 0.0 <= quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")
        
        self.source_quality[source_name] = quality_score
        logger.info(f"Set quality score for {source_name}: {quality_score}")
    
    def get_matches(self, cache_key: str) -> Optional[List[EntityMatch]]:
        """Get cached matches"""
        return self.match_cache.get(cache_key)
    
    def clear_cache(self):
        """Clear match cache"""
        self.match_cache.clear()
        logger.info("Match cache cleared")


# Singleton instance
_entity_matcher = None

def get_entity_matcher() -> EntityMatcher:
    """Get the singleton EntityMatcher instance"""
    global _entity_matcher
    if _entity_matcher is None:
        _entity_matcher = EntityMatcher()
    return _entity_matcher
