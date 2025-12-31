"""
Connection Management Module

Provides dynamic database connection management similar to ThoughtSpot.
"""

from src.connection.manager import ConnectionManager, get_connection_manager
from src.connection.models import (
    ConnectionConfig,
    ConnectionType,
    DatabaseSchema,
    TableMetadata,
    ColumnMetadata,
    ForeignKeyRelationship,
)

__all__ = [
    "ConnectionManager",
    "get_connection_manager",
    "ConnectionConfig",
    "ConnectionType",
    "DatabaseSchema",
    "TableMetadata",
    "ColumnMetadata",
    "ForeignKeyRelationship",
]
