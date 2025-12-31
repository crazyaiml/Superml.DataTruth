"""
Connection Data Models

Models for database connections, schema metadata, and relationships.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConnectionType(str, Enum):
    """Supported database connection types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"
    REDSHIFT = "redshift"
    BIGQUERY = "bigquery"
    SQLSERVER = "sqlserver"


class ConnectionConfig(BaseModel):
    """Database connection configuration."""
    
    id: str = Field(..., description="Unique connection identifier")
    name: str = Field(..., description="Display name for this connection")
    type: ConnectionType = Field(..., description="Database type")
    
    # Connection details
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password (encrypted)")
    
    # Additional settings
    schema_name: Optional[str] = Field("public", description="Default schema")
    ssl_enabled: bool = Field(False, description="Use SSL connection")
    pool_size: int = Field(5, description="Connection pool size")
    
    # Metadata
    is_active: bool = Field(True, description="Connection is active")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DataType(str, Enum):
    """Common data types."""
    INTEGER = "integer"
    BIGINT = "bigint"
    DECIMAL = "decimal"
    FLOAT = "float"
    STRING = "string"
    TEXT = "text"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"
    JSON = "json"
    ARRAY = "array"


class ColumnMetadata(BaseModel):
    """Metadata for a table column."""
    
    name: str = Field(..., description="Column name")
    data_type: DataType = Field(..., description="Column data type")
    is_nullable: bool = Field(True, description="Column allows NULL values")
    is_primary_key: bool = Field(False, description="Column is primary key")
    is_foreign_key: bool = Field(False, description="Column is foreign key")
    
    # Business metadata
    display_name: Optional[str] = Field(None, description="Business-friendly name")
    description: Optional[str] = Field(None, description="Column description")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    
    # For aggregations
    is_measure: bool = Field(False, description="Column is a numeric measure")
    is_dimension: bool = Field(False, description="Column is a dimension")
    default_aggregation: Optional[str] = Field(None, description="Default aggregation (sum, avg, count, etc.)")
    
    # Format
    format_string: Optional[str] = Field(None, description="Display format (e.g., $#,##0.00)")
    
    class Config:
        use_enum_values = True


class RelationshipCardinality(str, Enum):
    """Relationship cardinality types."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class ForeignKeyRelationship(BaseModel):
    """Foreign key relationship between tables."""
    
    from_table: str = Field(..., description="Source table")
    from_column: str = Field(..., description="Source column")
    to_table: str = Field(..., description="Target table")
    to_column: str = Field(..., description="Target column")
    cardinality: RelationshipCardinality = Field(..., description="Relationship cardinality")
    
    # Relationship metadata
    name: Optional[str] = Field(None, description="Relationship name")
    is_active: bool = Field(True, description="Relationship is active")


class TableMetadata(BaseModel):
    """Metadata for a database table."""
    
    model_config = {"protected_namespaces": ()}
    
    name: str = Field(..., description="Table name")
    schema: str = Field("public", description="Schema name")
    
    # Columns
    columns: List[ColumnMetadata] = Field(default_factory=list, description="Table columns")
    primary_keys: List[str] = Field(default_factory=list, description="Primary key columns")
    
    # Business metadata
    display_name: Optional[str] = Field(None, description="Business-friendly name")
    description: Optional[str] = Field(None, description="Table description")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    
    # Statistics
    row_count: Optional[int] = Field(None, description="Approximate row count")
    size_bytes: Optional[int] = Field(None, description="Table size in bytes")
    
    # Classification
    table_type: str = Field("fact", description="Table type: fact, dimension, bridge")
    tags: List[str] = Field(default_factory=list, description="Classification tags")


class DatabaseSchema(BaseModel):
    """Complete database schema metadata."""
    
    connection_id: str = Field(..., description="Connection identifier")
    schema_name: str = Field("public", description="Schema name")
    
    # Schema contents
    tables: Dict[str, TableMetadata] = Field(default_factory=dict, description="Tables in schema")
    relationships: List[ForeignKeyRelationship] = Field(default_factory=list, description="Foreign key relationships")
    
    # Metadata
    discovered_at: Optional[str] = Field(None, description="Schema discovery timestamp")
    table_count: int = Field(0, description="Number of tables")
    relationship_count: int = Field(0, description="Number of relationships")
