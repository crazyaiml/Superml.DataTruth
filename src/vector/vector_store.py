"""
Vector Store Manager

Manages ChromaDB for persistent semantic search of fields, metrics, and learned synonyms.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector embeddings for semantic search."""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create collections for different types of embeddings
        self._init_collections()
        
        logger.info(f"VectorStore initialized with persistence at {self.persist_directory}")
    
    def _init_collections(self):
        """Initialize ChromaDB collections."""
        # Fields collection: stores all database fields with their metadata
        self.fields_collection = self.client.get_or_create_collection(
            name="semantic_fields",
            metadata={"description": "Database fields with semantic metadata"}
        )
        
        # Synonyms collection: stores learned synonyms and mappings
        self.synonyms_collection = self.client.get_or_create_collection(
            name="learned_synonyms",
            metadata={"description": "Learned synonyms from query history"}
        )
        
        # Queries collection: stores successful queries for learning
        self.queries_collection = self.client.get_or_create_collection(
            name="query_history",
            metadata={"description": "Successful query patterns"}
        )
        
        logger.info("ChromaDB collections initialized")
    
    def add_field(
        self,
        connection_id: str,
        table_name: str,
        column_name: str,
        display_name: str,
        description: str,
        is_measure: bool,
        synonyms: List[str],
        data_type: str,
        default_aggregation: Optional[str] = None
    ):
        """
        Add or update a field embedding.
        
        Args:
            connection_id: Database connection ID
            table_name: Table name
            column_name: Column name
            display_name: Business-friendly display name
            description: Field description
            is_measure: Whether it's a metric (True) or dimension (False)
            synonyms: List of synonyms
            data_type: Data type (numeric, string, date, etc.)
            default_aggregation: Default aggregation (sum, avg, count, etc.)
        """
        field_id = f"{connection_id}:{table_name}.{column_name}"
        
        # Create rich text for embedding
        field_text = self._create_field_text(
            display_name=display_name,
            description=description,
            synonyms=synonyms,
            column_name=column_name
        )
        
        # Metadata - store complete field mapping info
        metadata = {
            "connection_id": connection_id,
            "table_name": table_name,
            "column_name": column_name,
            "display_name": display_name,
            "description": description,
            "is_measure": str(is_measure),
            "data_type": data_type,
            "field_type": "metric" if is_measure else "dimension",
            "default_aggregation": default_aggregation or "",
            "synonyms": ",".join(synonyms) if synonyms else ""
        }
        
        try:
            # Add to collection (upsert)
            self.fields_collection.upsert(
                ids=[field_id],
                documents=[field_text],
                metadatas=[metadata]
            )
            logger.debug(f"Added field embedding: {field_id}")
        except Exception as e:
            logger.error(f"Failed to add field embedding {field_id}: {e}")
    
    def _create_field_text(
        self,
        display_name: str,
        description: str,
        synonyms: List[str],
        column_name: str
    ) -> str:
        """Create rich text for field embedding."""
        parts = [
            f"Field: {display_name}",
            f"Column: {column_name}",
            f"Description: {description}",
        ]
        
        if synonyms:
            parts.append(f"Also known as: {', '.join(synonyms)}")
        
        return " | ".join(parts)
    
    def search_fields(
        self,
        query: str,
        connection_id: Optional[str] = None,
        field_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for fields semantically.
        
        Args:
            query: Search query (e.g., "daily stock change")
            connection_id: Filter by connection ID (optional)
            field_type: Filter by "metric" or "dimension" (optional)
            top_k: Number of results to return
        
        Returns:
            List of matching fields with metadata and scores
        """
        # Build where filter
        where_filter = {}
        if connection_id:
            where_filter["connection_id"] = connection_id
        if field_type:
            where_filter["field_type"] = field_type
        
        try:
            results = self.fields_collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter if where_filter else None
            )
            
            # Format results
            matches = []
            if results['ids'] and results['ids'][0]:
                for i, field_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    
                    matches.append({
                        "field_id": field_id,
                        "connection_id": metadata.get("connection_id"),
                        "table_name": metadata.get("table_name"),
                        "column_name": metadata.get("column_name"),
                        "display_name": metadata.get("display_name"),
                        "field_type": metadata.get("field_type"),
                        "data_type": metadata.get("data_type"),
                        "similarity": 1 - distance,  # Convert distance to similarity
                        "matched_text": results['documents'][0][i]
                    })
            
            return matches
        except Exception as e:
            logger.error(f"Field search failed: {e}")
            return []
    
    def add_learned_synonym(
        self,
        connection_id: str,
        user_term: str,
        matched_field: str,
        field_type: str,
        context: str = ""
    ):
        """
        Store a learned synonym mapping.
        
        Args:
            connection_id: Database connection ID
            user_term: What user said (e.g., "daily change")
            matched_field: What it matched to (e.g., "Price Change 24h")
            field_type: "metric" or "dimension"
            context: Additional context about the learning
        """
        synonym_id = f"{connection_id}:{user_term.lower()}:{matched_field}"
        
        # Create text for embedding
        synonym_text = f"User says '{user_term}' meaning '{matched_field}' | Context: {context}"
        
        metadata = {
            "connection_id": connection_id,
            "user_term": user_term.lower(),
            "matched_field": matched_field,
            "field_type": field_type
        }
        
        try:
            self.synonyms_collection.upsert(
                ids=[synonym_id],
                documents=[synonym_text],
                metadatas=[metadata]
            )
            logger.info(f"Learned synonym: '{user_term}' → '{matched_field}'")
        except Exception as e:
            logger.error(f"Failed to store learned synonym: {e}")
    
    def get_learned_synonyms(
        self,
        connection_id: str,
        field_type: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Get all learned synonyms for a connection.
        
        Args:
            connection_id: Database connection ID
            field_type: Filter by "metric" or "dimension" (optional)
        
        Returns:
            Dictionary of {field_name: [synonyms]}
        """
        where_filter = {"connection_id": connection_id}
        if field_type:
            where_filter["field_type"] = field_type
        
        try:
            # Get all synonyms for this connection
            results = self.synonyms_collection.get(
                where=where_filter,
                include=["metadatas"]
            )
            
            # Group by matched field
            synonyms_dict = {}
            if results['metadatas']:
                for metadata in results['metadatas']:
                    matched_field = metadata.get("matched_field")
                    user_term = metadata.get("user_term")
                    
                    if matched_field and user_term:
                        if matched_field not in synonyms_dict:
                            synonyms_dict[matched_field] = []
                        if user_term not in synonyms_dict[matched_field]:
                            synonyms_dict[matched_field].append(user_term)
            
            return synonyms_dict
        except Exception as e:
            logger.error(f"Failed to get learned synonyms: {e}")
            return {}
    
    def record_successful_query(
        self,
        connection_id: str,
        user_query: str,
        metric: str,
        dimensions: List[str],
        query_id: Optional[str] = None
    ):
        """
        Record a successful query pattern for learning.
        
        Args:
            connection_id: Database connection ID
            user_query: Original user question
            metric: Metric that was used
            dimensions: Dimensions that were used
            query_id: Optional unique query ID
        """
        if not query_id:
            import hashlib
            query_id = hashlib.md5(f"{connection_id}:{user_query}".encode()).hexdigest()[:16]
        
        query_text = f"Question: {user_query} | Metric: {metric} | Dimensions: {', '.join(dimensions)}"
        
        metadata = {
            "connection_id": connection_id,
            "metric": metric,
            "dimension_count": str(len(dimensions))
        }
        
        try:
            self.queries_collection.upsert(
                ids=[query_id],
                documents=[query_text],
                metadatas=[metadata]
            )
            logger.debug(f"Recorded successful query: {query_id}")
        except Exception as e:
            logger.error(f"Failed to record query: {e}")
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        return {
            "fields_count": self.fields_collection.count(),
            "learned_synonyms_count": self.synonyms_collection.count(),
            "queries_count": self.queries_collection.count(),
            "persist_directory": str(self.persist_directory)
        }
    
    def reset(self):
        """Reset all collections (for testing)."""
        logger.warning("Resetting all vector store collections")
        self.client.reset()
        self._init_collections()


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
