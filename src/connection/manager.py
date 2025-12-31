"""
Connection Manager

Manages database connections and schema introspection.
Connections are persisted in the internal database.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
from psycopg2.pool import SimpleConnectionPool

from src.connection.models import (
    ColumnMetadata,
    ConnectionConfig,
    ConnectionType,
    DatabaseSchema,
    DataType,
    ForeignKeyRelationship,
    RelationshipCardinality,
    TableMetadata,
)
from src.database.internal_db import InternalDB

logger = logging.getLogger(__name__)

# Singleton instance
_connection_manager = None


class ConnectionManager:
    """
    Manages database connections and schema introspection.
    
    Similar to ThoughtSpot's connection management:
    1. Connect to data source
    2. Discover schema (tables, columns, relationships)
    3. Auto-detect foreign keys and cardinality
    
    Connections are persisted in the internal DataTruth database.
    """
    
    def __init__(self):
        """Initialize connection manager and load from database."""
        self.connections: Dict[str, ConnectionConfig] = {}
        self.pools: Dict[str, SimpleConnectionPool] = {}
        self.schemas: Dict[str, DatabaseSchema] = {}
        
        # Load existing connections from database
        self._load_connections_from_db()
    
    def _load_connections_from_db(self) -> None:
        """Load all connections from the internal database."""
        try:
            logger.info("Loading connections from internal database...")
            connections_data = InternalDB.load_connections()
            logger.info(f"Found {len(connections_data)} connections in database")
            
            for conn_data in connections_data:
                try:
                    # Convert database row to ConnectionConfig
                    config = ConnectionConfig(
                        id=conn_data['id'],
                        name=conn_data['name'],
                        type=ConnectionType(conn_data['type']),
                        host=conn_data.get('host'),
                        port=conn_data.get('port'),
                        database=conn_data['database'],
                        username=conn_data['username'],
                        password=conn_data['password'],
                        schema_name=conn_data.get('schema_name', 'public')
                    )
                    self.connections[config.id] = config
                    
                    # Create connection pool for PostgreSQL connections
                    if config.type == ConnectionType.POSTGRESQL:
                        try:
                            pool = SimpleConnectionPool(
                                minconn=1,
                                maxconn=config.pool_size,
                                host=config.host,
                                port=config.port or 5432,
                                database=config.database,
                                user=config.username,
                                password=config.password
                            )
                            self.pools[config.id] = pool
                            logger.info(f"✓ Loaded connection from DB: {config.name} (id={config.id}) with pool")
                        except Exception as e:
                            logger.error(f"Failed to create pool for {config.id}: {e}")
                    else:
                        logger.info(f"✓ Loaded connection from DB: {config.name} (id={config.id})")
                        
                except Exception as e:
                    logger.error(f"Failed to load connection {conn_data.get('id')}: {e}")
        except Exception as e:
            logger.error(f"Failed to load connections from database: {e}")
    
    def add_connection(self, config: ConnectionConfig, test_connection: bool = False) -> dict:
        """
        Add a new database connection and persist to database.
        
        Args:
            config: Connection configuration
            test_connection: If True, test connection and raise error if it fails
            
        Returns:
            dict with status information
        """
        self.connections[config.id] = config
        
        # Save to internal database
        connection_data = {
            'id': config.id,
            'name': config.name,
            'description': '',  # Can be added to ConnectionConfig later
            'type': config.type.value,
            'host': config.host,
            'port': config.port or 5432,
            'database': config.database,
            'username': config.username,
            'password': config.password,  # TODO: Encrypt this!
            'schema_name': config.schema_name or 'public'
        }
        
        success = InternalDB.save_connection(connection_data)
        if success:
            logger.info(f"✓ Saved connection to database: {config.name} (id={config.id})")
        else:
            logger.warning(f"Failed to persist connection {config.id} to database")
        
        result = {
            'saved': success,
            'connection_id': config.id,
            'pool_created': False,
            'pool_error': None
        }
        
        # Try to create connection pool for PostgreSQL (optional)
        if config.type == ConnectionType.POSTGRESQL:
            try:
                pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=config.pool_size,
                    host=config.host,
                    port=config.port or 5432,
                    database=config.database,
                    user=config.username,
                    password=config.password
                )
                self.pools[config.id] = pool
                result['pool_created'] = True
                logger.info(f"Created connection pool for {config.name} ({config.id})")
            except Exception as e:
                result['pool_error'] = str(e)
                logger.warning(f"Connection saved but pool creation failed: {e}")
                if test_connection:
                    raise  # Only raise if explicitly testing connection
        
        return result
    
    def get_connection(self, connection_id: str):
        """Get a connection from the pool."""
        if connection_id not in self.pools:
            raise ValueError(f"Connection not found: {connection_id}")
        
        pool = self.pools[connection_id]
        return pool.getconn()
    
    def get_connection_config(self, connection_id: str) -> Optional[ConnectionConfig]:
        """Get connection configuration by ID."""
        return self.connections.get(connection_id)
    
    def release_connection(self, connection_id: str, conn):
        """Release a connection back to the pool."""
        if connection_id in self.pools:
            self.pools[connection_id].putconn(conn)
    
    def discover_schema(self, connection_id: str) -> DatabaseSchema:
        """
        Discover database schema (ThoughtSpot Step 1).
        
        Introspects the database to find:
        - All tables
        - All columns with data types
        - Primary keys
        - Foreign key relationships
        - Relationship cardinality
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Complete database schema
        """
        if connection_id not in self.connections:
            raise ValueError(f"Connection not found: {connection_id}")
        
        config = self.connections[connection_id]
        logger.info(f"Discovering schema for {config.name}")
        
        # Get connection
        conn = self.get_connection(connection_id)
        
        try:
            schema = DatabaseSchema(
                connection_id=connection_id,
                schema_name=config.schema_name,
                discovered_at=datetime.utcnow().isoformat()
            )
            
            # Discover tables
            tables = self._discover_tables(conn, config.schema_name)
            schema.tables = {table.name: table for table in tables}
            schema.table_count = len(tables)
            
            # Discover relationships
            relationships = self._discover_relationships(conn, config.schema_name)
            schema.relationships = relationships
            schema.relationship_count = len(relationships)
            
            # Store schema
            self.schemas[connection_id] = schema
            
            # Update connection stats in database
            InternalDB.update_connection_stats(
                connection_id=connection_id,
                table_count=schema.table_count,
                relationship_count=schema.relationship_count
            )
            
            logger.info(
                f"Discovered {schema.table_count} tables and "
                f"{schema.relationship_count} relationships"
            )
            
            return schema
            
        finally:
            self.release_connection(connection_id, conn)
    
    def _discover_tables(self, conn, schema_name: str) -> List[TableMetadata]:
        """Discover all tables in the schema."""
        tables = []
        
        with conn.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, (schema_name,))
            
            for (table_name,) in cursor.fetchall():
                # Get columns for each table
                columns = self._discover_columns(conn, schema_name, table_name)
                
                # Get primary keys
                primary_keys = self._discover_primary_keys(conn, schema_name, table_name)
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
                row_count = cursor.fetchone()[0]
                
                table = TableMetadata(
                    name=table_name,
                    schema=schema_name,
                    columns=columns,
                    primary_keys=primary_keys,
                    row_count=row_count
                )
                
                # Auto-classify as fact or dimension
                table.table_type = self._classify_table(table)
                
                tables.append(table)
        
        return tables
    
    def _discover_columns(
        self, conn, schema_name: str, table_name: str
    ) -> List[ColumnMetadata]:
        """Discover columns for a table."""
        columns = []
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                ORDER BY ordinal_position
            """, (schema_name, table_name))
            
            for row in cursor.fetchall():
                column_name, data_type, is_nullable, column_default = row
                
                # Map PostgreSQL types to our DataType enum
                mapped_type = self._map_data_type(data_type)
                
                # Detect if it's a measure (numeric) or dimension
                is_measure = mapped_type in [
                    DataType.INTEGER, DataType.BIGINT,
                    DataType.DECIMAL, DataType.FLOAT
                ]
                
                column = ColumnMetadata(
                    name=column_name,
                    data_type=mapped_type,
                    is_nullable=(is_nullable == 'YES'),
                    is_measure=is_measure,
                    is_dimension=not is_measure
                )
                
                # Set default aggregation for measures
                if is_measure:
                    # Amount/revenue fields default to SUM
                    if any(keyword in column_name.lower() for keyword in ['amount', 'revenue', 'price', 'cost', 'total']):
                        column.default_aggregation = 'sum'
                    # Count fields stay as-is
                    elif 'count' in column_name.lower():
                        column.default_aggregation = 'sum'
                    # Others default to AVG
                    else:
                        column.default_aggregation = 'avg'
                
                columns.append(column)
        
        return columns
    
    def _discover_primary_keys(
        self, conn, schema_name: str, table_name: str
    ) -> List[str]:
        """Discover primary key columns for a table."""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid
                    AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                  AND i.indisprimary
            """, (f"{schema_name}.{table_name}",))
            
            return [row[0] for row in cursor.fetchall()]
    
    def _discover_relationships(
        self, conn, schema_name: str
    ) -> List[ForeignKeyRelationship]:
        """Discover foreign key relationships."""
        relationships = []
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tc.table_name AS from_table,
                    kcu.column_name AS from_column,
                    ccu.table_name AS to_table,
                    ccu.column_name AS to_column,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = %s
            """, (schema_name,))
            
            for row in cursor.fetchall():
                from_table, from_column, to_table, to_column, constraint_name = row
                
                # Detect cardinality
                cardinality = self._detect_cardinality(
                    conn, schema_name, from_table, from_column, to_table, to_column
                )
                
                relationship = ForeignKeyRelationship(
                    from_table=from_table,
                    from_column=from_column,
                    to_table=to_table,
                    to_column=to_column,
                    cardinality=cardinality,
                    name=constraint_name
                )
                
                relationships.append(relationship)
        
        return relationships
    
    def _detect_cardinality(
        self, conn, schema_name: str,
        from_table: str, from_column: str,
        to_table: str, to_column: str
    ) -> RelationshipCardinality:
        """
        Detect relationship cardinality (1:1, 1:N, N:1, N:N).
        
        Logic:
        - If from_column is unique → Many-to-One or One-to-One
        - If to_column is unique → One-to-Many or One-to-One
        - If both unique → One-to-One
        - If neither unique → Many-to-Many (rare with FK)
        """
        with conn.cursor() as cursor:
            # Check if from_column is unique
            cursor.execute(f"""
                SELECT COUNT(*) = COUNT(DISTINCT {from_column})
                FROM {schema_name}.{from_table}
            """)
            from_is_unique = cursor.fetchone()[0]
            
            # Check if to_column is unique (usually PK)
            cursor.execute(f"""
                SELECT COUNT(*) = COUNT(DISTINCT {to_column})
                FROM {schema_name}.{to_table}
            """)
            to_is_unique = cursor.fetchone()[0]
            
            if from_is_unique and to_is_unique:
                return RelationshipCardinality.ONE_TO_ONE
            elif from_is_unique:
                return RelationshipCardinality.MANY_TO_ONE
            elif to_is_unique:
                return RelationshipCardinality.ONE_TO_MANY
            else:
                return RelationshipCardinality.MANY_TO_MANY
    
    def _map_data_type(self, pg_type: str) -> DataType:
        """Map PostgreSQL data types to our DataType enum."""
        type_lower = pg_type.lower()
        
        if type_lower in ['integer', 'smallint', 'int', 'int4']:
            return DataType.INTEGER
        elif type_lower in ['bigint', 'int8']:
            return DataType.BIGINT
        elif type_lower in ['numeric', 'decimal']:
            return DataType.DECIMAL
        elif type_lower in ['real', 'double precision', 'float', 'float8']:
            return DataType.FLOAT
        elif type_lower in ['character varying', 'varchar', 'character', 'char']:
            return DataType.STRING
        elif type_lower == 'text':
            return DataType.TEXT
        elif type_lower == 'date':
            return DataType.DATE
        elif type_lower in ['timestamp', 'timestamp without time zone', 'timestamp with time zone']:
            return DataType.TIMESTAMP
        elif type_lower == 'boolean':
            return DataType.BOOLEAN
        elif type_lower in ['json', 'jsonb']:
            return DataType.JSON
        elif type_lower == 'array':
            return DataType.ARRAY
        else:
            return DataType.STRING  # Default fallback
    
    def _classify_table(self, table: TableMetadata) -> str:
        """
        Auto-classify table as fact or dimension.
        
        Heuristics:
        - Tables with many numeric columns → likely fact tables
        - Tables with mostly categorical columns → likely dimension tables
        - Table names ending in 's' → likely dimension (plural entities)
        """
        measure_count = sum(1 for col in table.columns if col.is_measure)
        dimension_count = sum(1 for col in table.columns if col.is_dimension)
        
        # If more measures than dimensions, likely a fact table
        if measure_count > dimension_count:
            return "fact"
        else:
            return "dimension"
    
    def get_schema(self, connection_id: str) -> Optional[DatabaseSchema]:
        """Get discovered schema for a connection."""
        return self.schemas.get(connection_id)
    
    def list_connections(self) -> List[ConnectionConfig]:
        """List all configured connections."""
        return list(self.connections.values())


def get_connection_manager() -> ConnectionManager:
    """Get singleton ConnectionManager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
