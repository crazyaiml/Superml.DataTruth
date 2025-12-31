"""
Semantic Matcher

Uses embeddings for intelligent semantic matching of metrics and dimensions.
Provides fuzzy matching beyond exact string comparison.

Now enhanced with persistent vector storage via ChromaDB.
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import numpy (optional)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy not available, using basic matching only")

# Singleton instance
_semantic_matcher = None


class SemanticMatcher:
    """
    AI-powered semantic matching for metrics and dimensions.
    
    Uses embeddings to find semantically similar names even when
    they don't match exactly. Enhanced with persistent vector storage.
    """
    
    def __init__(self, vector_store=None):
        """
        Initialize semantic matcher.
        
        Args:
            vector_store: Optional VectorStore instance for persistent search
        """
        self.vector_store = vector_store
        self.use_embeddings = False
        self.embeddings_cache = {}
        
        # Check if numpy is available
        if not HAS_NUMPY:
            logger.info("Semantic matcher initialized with token-based matching only (numpy not available)")
            self.model = None
            return
        
        # Try to initialize sentence transformers
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.use_embeddings = True
            logger.info("Semantic matcher initialized with embeddings")
        except ImportError:
            logger.warning("sentence-transformers not available, using fallback matching")
            self.model = None
    
    def _get_embedding(self, text: str):
        """Get embedding for text (with caching)."""
        if not self.use_embeddings or not HAS_NUMPY:
            return None
        
        cache_key = text.lower()
        if cache_key not in self.embeddings_cache:
            self.embeddings_cache[cache_key] = self.model.encode(text)
        return self.embeddings_cache[cache_key]
    
    def _cosine_similarity(self, emb1, emb2) -> float:
        """Calculate cosine similarity between embeddings."""
        if not HAS_NUMPY:
            return 0.0
        import numpy as np
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
    
    def find_best_match(
        self,
        query_term: str,
        available_names: List[str],
        threshold: float = 0.7,
        connection_id: Optional[str] = None,
        field_type: Optional[str] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Find best semantic match for a query term.
        
        Args:
            query_term: User's search term
            available_names: List of available metric/dimension names
            threshold: Minimum similarity score (0-1)
            connection_id: Optional connection ID for vector store search
            field_type: Optional field type ("metric" or "dimension") for filtering
            
        Returns:
            Tuple of (matched_name, similarity_score) or None
        """
        if not available_names:
            return None
        
        # Try vector store first if available and connection_id provided
        if self.vector_store and connection_id:
            vector_match = self._vector_store_match(
                query_term, available_names, threshold, connection_id, field_type
            )
            if vector_match:
                return vector_match
        
        # If embeddings available, use semantic matching
        if self.use_embeddings:
            return self._embedding_match(query_term, available_names, threshold)
        
        # Fallback: token-based matching
        return self._token_match(query_term, available_names, threshold)
    
    def _vector_store_match(
        self,
        query_term: str,
        available_names: List[str],
        threshold: float,
        connection_id: str,
        field_type: Optional[str]
    ) -> Optional[Tuple[str, float]]:
        """Match using vector store."""
        try:
            matches = self.vector_store.search_fields(
                query=query_term,
                connection_id=connection_id,
                field_type=field_type,
                top_k=10
            )
            
            # Find best match from available names
            for match in matches:
                display_name = match.get("display_name")
                similarity = match.get("similarity", 0)
                
                if display_name in available_names and similarity >= threshold:
                    logger.info(f"Vector store match: '{query_term}' -> '{display_name}' (score: {similarity:.2f})")
                    return (display_name, similarity)
            
        except Exception as e:
            logger.warning(f"Vector store search failed: {e}, falling back to embedding match")
        
        return None
    
    def _embedding_match(
        self,
        query_term: str,
        available_names: List[str],
        threshold: float
    ) -> Optional[Tuple[str, float]]:
        """Match using embeddings."""
        query_emb = self._get_embedding(query_term)
        
        best_match = None
        best_score = 0.0
        
        for name in available_names:
            name_emb = self._get_embedding(name)
            similarity = self._cosine_similarity(query_emb, name_emb)
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = name
        
        if best_match:
            logger.info(f"Semantic match: '{query_term}' -> '{best_match}' (score: {best_score:.2f})")
            return (best_match, best_score)
        
        return None
    
    def _token_match(
        self,
        query_term: str,
        available_names: List[str],
        threshold: float
    ) -> Optional[Tuple[str, float]]:
        """Fallback token-based matching."""
        query_tokens = set(query_term.lower().replace('_', ' ').replace('-', ' ').split())
        
        best_match = None
        best_score = 0.0
        
        for name in available_names:
            name_tokens = set(name.lower().replace('_', ' ').replace('-', ' ').split())
            
            # Jaccard similarity
            intersection = query_tokens & name_tokens
            union = query_tokens | name_tokens
            
            if union:
                similarity = len(intersection) / len(union)
                
                # Bonus for exact substring match
                if query_term.lower() in name.lower() or name.lower() in query_term.lower():
                    similarity += 0.3
                
                similarity = min(similarity, 1.0)
                
                if similarity > best_score and similarity >= threshold:
                    best_score = similarity
                    best_match = name
        
        if best_match:
            logger.info(f"Token match: '{query_term}' -> '{best_match}' (score: {best_score:.2f})")
            return (best_match, best_score)
        
        return None
    
    def batch_match(
        self,
        query_terms: List[str],
        available_names: List[str],
        threshold: float = 0.7
    ) -> List[Optional[Tuple[str, float]]]:
        """Match multiple terms at once."""
        return [self.find_best_match(term, available_names, threshold) for term in query_terms]
    
    def get_top_matches(
        self,
        query_term: str,
        available_names: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Get top K matches for a query term."""
        if not available_names:
            return []
        
        matches = []
        
        if self.use_embeddings:
            query_emb = self._get_embedding(query_term)
            for name in available_names:
                name_emb = self._get_embedding(name)
                similarity = self._cosine_similarity(query_emb, name_emb)
                matches.append((name, similarity))
        else:
            # Token-based matching
            query_tokens = set(query_term.lower().replace('_', ' ').replace('-', ' ').split())
            for name in available_names:
                name_tokens = set(name.lower().replace('_', ' ').replace('-', ' ').split())
                intersection = query_tokens & name_tokens
                union = query_tokens | name_tokens
                similarity = len(intersection) / len(union) if union else 0
                matches.append((name, similarity))
        
        # Sort by similarity and return top K
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_k]


def get_semantic_matcher() -> SemanticMatcher:
    """Get or create the singleton SemanticMatcher instance."""
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher()
    return _semantic_matcher
