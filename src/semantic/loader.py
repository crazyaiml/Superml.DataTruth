"""
Semantic Layer Loader

Database-driven semantic layer - all configurations stored in PostgreSQL.
No YAML files required.
"""

from typing import Dict, List

from src.semantic.models import (
    Dimension,
    Join,
    JoinPreference,
    Metric,
    SemanticLayer,
)


class SemanticLayerLoader:
    """Database-driven semantic layer loader. All configs come from PostgreSQL."""

    def __init__(self) -> None:
        """Initialize the loader with empty semantic layer."""
        self._semantic_layer: SemanticLayer | None = None

    def load(self) -> SemanticLayer:
        """
        Load empty semantic layer structure.
        
        All metrics, dimensions, and configurations are now stored in PostgreSQL
        and loaded per-connection via the API/UI.
        
        Returns:
            Empty SemanticLayer instance (to be populated from database).
        """
        # Return empty semantic layer - all data comes from database now
        self._semantic_layer = SemanticLayer(
            metrics={},
            dimensions={},
            joins=[],
            join_preferences=[],
            synonyms={},
        )

        return self._semantic_layer

    @property
    def semantic_layer(self) -> SemanticLayer:
        """Get loaded semantic layer (loads if not already loaded)."""
        if self._semantic_layer is None:
            self.load()
        return self._semantic_layer

# Global semantic layer instance
_loader = SemanticLayerLoader()


def get_semantic_layer() -> SemanticLayer:
    """
    Get the global semantic layer instance.
    
    Returns empty structure - all semantic layer data now comes from PostgreSQL.
    Use the database tables (calculated_metrics, field_mappings, etc.) for actual data.
    
    Returns:
        Empty SemanticLayer instance.
    """
    return _loader.semantic_layer


def reload_semantic_layer() -> SemanticLayer:
    """
    Reload the semantic layer.
    
    Returns:
        Newly loaded (empty) SemanticLayer instance.
    """
    global _loader
    _loader = SemanticLayerLoader()
    return _loader.load()
