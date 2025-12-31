"""
Semantic Search Index - Phase 2: Fast vector search with ChromaDB

This module provides vector-based semantic search for metrics, dimensions,
and synonyms using ChromaDB for efficient similarity search.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with relevance score"""
    id: str
    type: str  # 'metric', 'dimension', 'synonym'
    name: str
    description: Optional[str]
    metadata: Dict
    relevance_score: float
    matched_term: str  # The specific term that matched


class SemanticSearchIndex:
    """
    Vector-based semantic search index using ChromaDB.
    
    Features:
    - Fast cosine similarity search
    - Indexes metrics, dimensions, and synonyms
    - Automatic embedding generation
    - Persistent storage
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, persist_directory: str = "./chroma_db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._persist_directory = persist_directory
                    cls._instance = instance
        return cls._instance
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # Use the persist_directory from __new__ if available
        if hasattr(self, '_persist_directory'):
            persist_directory = self._persist_directory
        
        # Initialize ChromaDB
        logger.info("Initializing ChromaDB...")
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Load sentence transformer model
        logger.info("Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
        
        # Create or get collections
        self.metrics_collection = self.client.get_or_create_collection(
            name="metrics",
            metadata={"description": "Metric definitions and synonyms"}
        )
        
        self.dimensions_collection = self.client.get_or_create_collection(
            name="dimensions",
            metadata={"description": "Dimension definitions and synonyms"}
        )
        
        self.synonyms_collection = self.client.get_or_create_collection(
            name="synonyms",
            metadata={"description": "All synonyms (official + learned)"}
        )
        
        logger.info("Search index initialized successfully")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def index_metric(
        self,
        metric_name: str,
        description: str,
        synonyms: List[str],
        metadata: Optional[Dict] = None
    ):
        """
        Index a metric and its synonyms
        
        Args:
            metric_name: Name of the metric
            description: Description of the metric
            synonyms: List of synonyms
            metadata: Additional metadata
        """
        # Index the metric itself
        metric_id = f"metric:{metric_name}"
        metric_text = f"{metric_name} {description}"
        metric_embedding = self._generate_embedding(metric_text)
        
        self.metrics_collection.add(
            ids=[metric_id],
            embeddings=[metric_embedding],
            metadatas=[{
                'name': metric_name,
                'description': description,
                'type': 'metric',
                'indexed_at': datetime.now().isoformat(),
                **(metadata or {})
            }],
            documents=[metric_text]
        )
        
        # Index synonyms
        for idx, synonym in enumerate(synonyms):
            synonym_id = f"metric_syn:{metric_name}:{idx}"
            synonym_embedding = self._generate_embedding(synonym)
            
            self.synonyms_collection.add(
                ids=[synonym_id],
                embeddings=[synonym_embedding],
                metadatas=[{
                    'name': metric_name,
                    'synonym': synonym,
                    'type': 'metric',
                    'indexed_at': datetime.now().isoformat()
                }],
                documents=[synonym]
            )
        
        logger.info(f"Indexed metric '{metric_name}' with {len(synonyms)} synonyms")
    
    def index_dimension(
        self,
        dimension_name: str,
        description: str,
        synonyms: List[str],
        metadata: Optional[Dict] = None
    ):
        """
        Index a dimension and its synonyms
        
        Args:
            dimension_name: Name of the dimension
            description: Description of the dimension
            synonyms: List of synonyms
            metadata: Additional metadata
        """
        # Index the dimension itself
        dimension_id = f"dimension:{dimension_name}"
        dimension_text = f"{dimension_name} {description}"
        dimension_embedding = self._generate_embedding(dimension_text)
        
        self.dimensions_collection.add(
            ids=[dimension_id],
            embeddings=[dimension_embedding],
            metadatas=[{
                'name': dimension_name,
                'description': description,
                'type': 'dimension',
                'indexed_at': datetime.now().isoformat(),
                **(metadata or {})
            }],
            documents=[dimension_text]
        )
        
        # Index synonyms
        for idx, synonym in enumerate(synonyms):
            synonym_id = f"dimension_syn:{dimension_name}:{idx}"
            synonym_embedding = self._generate_embedding(synonym)
            
            self.synonyms_collection.add(
                ids=[synonym_id],
                embeddings=[synonym_embedding],
                metadatas=[{
                    'name': dimension_name,
                    'synonym': synonym,
                    'type': 'dimension',
                    'indexed_at': datetime.now().isoformat()
                }],
                documents=[synonym]
            )
        
        logger.info(f"Indexed dimension '{dimension_name}' with {len(synonyms)} synonyms")
    
    def search(
        self,
        query: str,
        search_type: Optional[str] = None,  # 'metric', 'dimension', or None for both
        top_k: int = 5,
        min_relevance: float = 0.6
    ) -> List[SearchResult]:
        """
        Search for relevant items using semantic similarity
        
        Args:
            query: Natural language query
            search_type: Type of items to search for (None for all)
            top_k: Maximum number of results to return
            min_relevance: Minimum relevance score (0-1)
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        query_embedding = self._generate_embedding(query)
        results = []
        
        # Search metrics
        if search_type is None or search_type == 'metric':
            metric_results = self.metrics_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            if metric_results['ids'] and metric_results['ids'][0]:
                for i, (id, distance, metadata, document) in enumerate(zip(
                    metric_results['ids'][0],
                    metric_results['distances'][0],
                    metric_results['metadatas'][0],
                    metric_results['documents'][0]
                )):
                    # Convert distance to similarity score (1 - normalized distance)
                    relevance = 1 - (distance / 2)  # Assuming distance is L2
                    
                    if relevance >= min_relevance:
                        results.append(SearchResult(
                            id=id,
                            type='metric',
                            name=metadata['name'],
                            description=metadata.get('description'),
                            metadata=metadata,
                            relevance_score=relevance,
                            matched_term=document
                        ))
            
            # Search metric synonyms
            synonym_results = self.synonyms_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={'type': 'metric'} if search_type == 'metric' else None
            )
            
            if synonym_results['ids'] and synonym_results['ids'][0]:
                for i, (id, distance, metadata, document) in enumerate(zip(
                    synonym_results['ids'][0],
                    synonym_results['distances'][0],
                    synonym_results['metadatas'][0],
                    synonym_results['documents'][0]
                )):
                    relevance = 1 - (distance / 2)
                    
                    if relevance >= min_relevance:
                        results.append(SearchResult(
                            id=id,
                            type='metric',
                            name=metadata['name'],
                            description=None,
                            metadata=metadata,
                            relevance_score=relevance,
                            matched_term=metadata['synonym']
                        ))
        
        # Search dimensions
        if search_type is None or search_type == 'dimension':
            dimension_results = self.dimensions_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            if dimension_results['ids'] and dimension_results['ids'][0]:
                for i, (id, distance, metadata, document) in enumerate(zip(
                    dimension_results['ids'][0],
                    dimension_results['distances'][0],
                    dimension_results['metadatas'][0],
                    dimension_results['documents'][0]
                )):
                    relevance = 1 - (distance / 2)
                    
                    if relevance >= min_relevance:
                        results.append(SearchResult(
                            id=id,
                            type='dimension',
                            name=metadata['name'],
                            description=metadata.get('description'),
                            metadata=metadata,
                            relevance_score=relevance,
                            matched_term=document
                        ))
            
            # Search dimension synonyms
            synonym_results = self.synonyms_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={'type': 'dimension'} if search_type == 'dimension' else None
            )
            
            if synonym_results['ids'] and synonym_results['ids'][0]:
                for i, (id, distance, metadata, document) in enumerate(zip(
                    synonym_results['ids'][0],
                    synonym_results['distances'][0],
                    synonym_results['metadatas'][0],
                    synonym_results['documents'][0]
                )):
                    relevance = 1 - (distance / 2)
                    
                    if relevance >= min_relevance:
                        results.append(SearchResult(
                            id=id,
                            type='dimension',
                            name=metadata['name'],
                            description=None,
                            metadata=metadata,
                            relevance_score=relevance,
                            matched_term=metadata['synonym']
                        ))
        
        # Remove duplicates (keep highest relevance)
        seen = {}
        for result in results:
            key = (result.type, result.name)
            if key not in seen or result.relevance_score > seen[key].relevance_score:
                seen[key] = result
        
        # Sort by relevance and return top k
        final_results = sorted(seen.values(), key=lambda x: x.relevance_score, reverse=True)
        return final_results[:top_k]
    
    def build_index_from_semantic_layer(self, semantic_layer):
        """
        Build complete index from semantic layer configuration
        
        Args:
            semantic_layer: AgenticSemanticLayer instance
        """
        logger.info("Building search index from semantic layer...")
        
        # Clear existing indices
        self.clear_index()
        
        # Index all metrics
        for metric_name, metric_def in semantic_layer.metrics.items():
            self.index_metric(
                metric_name=metric_name,
                description=metric_def.description,
                synonyms=metric_def.synonyms,
                metadata={
                    'formula': metric_def.formula,
                    'aggregation': metric_def.aggregation.value,
                    'data_type': metric_def.data_type.value
                }
            )
        
        # Index all dimensions
        for dim_name, dim_def in semantic_layer.dimensions.items():
            self.index_dimension(
                dimension_name=dim_name,
                description=dim_def.description,
                synonyms=dim_def.synonyms,
                metadata={
                    'table': dim_def.table or '',
                    'type': dim_def.type.value
                }
            )
        
        logger.info(
            f"Index built: {len(semantic_layer.metrics)} metrics, "
            f"{len(semantic_layer.dimensions)} dimensions"
        )
    
    def clear_index(self):
        """Clear all indexed data"""
        logger.info("Clearing search index...")
        
        try:
            self.client.delete_collection("metrics")
            self.client.delete_collection("dimensions")
            self.client.delete_collection("synonyms")
            
            # Recreate collections
            self.metrics_collection = self.client.get_or_create_collection(
                name="metrics",
                metadata={"description": "Metric definitions and synonyms"}
            )
            
            self.dimensions_collection = self.client.get_or_create_collection(
                name="dimensions",
                metadata={"description": "Dimension definitions and synonyms"}
            )
            
            self.synonyms_collection = self.client.get_or_create_collection(
                name="synonyms",
                metadata={"description": "All synonyms (official + learned)"}
            )
            
            logger.info("Index cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
    
    def get_stats(self) -> Dict:
        """Get statistics about the search index"""
        return {
            'metrics_count': self.metrics_collection.count(),
            'dimensions_count': self.dimensions_collection.count(),
            'synonyms_count': self.synonyms_collection.count(),
            'total_indexed': (
                self.metrics_collection.count() +
                self.dimensions_collection.count() +
                self.synonyms_collection.count()
            )
        }


# Singleton instance
_search_index = None

def get_search_index(persist_directory: str = "./chroma_db") -> SemanticSearchIndex:
    """Get the singleton SemanticSearchIndex instance"""
    global _search_index
    if _search_index is None:
        _search_index = SemanticSearchIndex(persist_directory)
    return _search_index
