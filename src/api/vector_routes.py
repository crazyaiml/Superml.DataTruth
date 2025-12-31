"""
Vector DB Admin Routes

Endpoints for managing and inspecting the vector database.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.vector import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vector", tags=["vector"])


# Response models
class VectorStatsResponse(BaseModel):
    """Vector DB statistics."""
    fields_count: int
    learned_synonyms_count: int
    queries_count: int
    persist_directory: str


class FieldSearchRequest(BaseModel):
    """Request to search for fields."""
    query: str
    connection_id: Optional[str] = None
    field_type: Optional[str] = None
    top_k: int = 10


class LearnedSynonymsResponse(BaseModel):
    """Learned synonyms for a connection."""
    connection_id: str
    synonyms: dict


# Endpoints

@router.get("/stats", response_model=VectorStatsResponse)
async def get_vector_stats():
    """
    Get vector database statistics.
    
    Returns counts and metadata about stored embeddings.
    """
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        return VectorStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get vector stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/fields")
async def search_fields(request: FieldSearchRequest):
    """
    Search for fields across connections using semantic search.
    
    This endpoint enables cross-database field discovery - find similar
    fields across all connections or within a specific connection.
    """
    try:
        vector_store = get_vector_store()
        
        matches = vector_store.search_fields(
            query=request.query,
            connection_id=request.connection_id,
            field_type=request.field_type,
            top_k=request.top_k
        )
        
        return {
            "query": request.query,
            "matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        logger.error(f"Field search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synonyms/{connection_id}", response_model=LearnedSynonymsResponse)
async def get_learned_synonyms(
    connection_id: str,
    field_type: Optional[str] = Query(None, description="Filter by 'metric' or 'dimension'")
):
    """
    Get learned synonyms for a connection.
    
    Shows what user terms map to which fields based on query history.
    """
    try:
        vector_store = get_vector_store()
        
        synonyms = vector_store.get_learned_synonyms(
            connection_id=connection_id,
            field_type=field_type
        )
        
        return LearnedSynonymsResponse(
            connection_id=connection_id,
            synonyms=synonyms
        )
    except Exception as e:
        logger.error(f"Failed to get learned synonyms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reset")
async def reset_vector_store():
    """
    Reset all vector store collections.
    
    ⚠️ WARNING: This will delete all learned patterns and embeddings!
    Use with caution, typically only in development/testing.
    """
    try:
        vector_store = get_vector_store()
        vector_store.reset()
        
        return {
            "message": "Vector store reset successfully",
            "warning": "All learned patterns and embeddings have been deleted"
        }
    except Exception as e:
        logger.error(f"Failed to reset vector store: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def vector_health():
    """Check if vector store is operational."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return {
            "status": "healthy",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
