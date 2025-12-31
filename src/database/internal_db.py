"""
Internal Database Utility

Handles operations with the internal DataTruth metadata database.
This database stores:
- Users, roles, permissions
- Connection configurations
- Field mappings
- Query history and audit logs
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class InternalDB:
    """Utility class for internal database operations."""
    
    @staticmethod
    def get_connection():
        """Get a connection to the internal database."""
        return psycopg2.connect(
            host=settings.internal_db_host,
            port=settings.internal_db_port,
            database=settings.internal_db_name,
            user=settings.internal_db_user,
            password=settings.internal_db_password,
            cursor_factory=RealDictCursor
        )
    
    @staticmethod
    def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = True):
        """
        Execute a SQL query on the internal database.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: If True, fetch only one result
            fetch_all: If True, fetch all results (default)
            
        Returns:
            Query results or None
        """
        conn = None
        cursor = None
        try:
            conn = InternalDB.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Check if query has RETURNING clause or is a SELECT
            query_upper = query.strip().upper()
            if query_upper.startswith('SELECT') or 'RETURNING' in query_upper:
                # Check fetch_one FIRST before fetch_all
                if fetch_one:
                    result = cursor.fetchone()
                    conn.commit()  # Commit for RETURNING queries
                    return result
                elif fetch_all:
                    result = cursor.fetchall()
                    conn.commit()  # Commit for RETURNING queries
                    return result
                else:
                    conn.commit()  # Commit even if not fetching
                    return None
            else:
                # For INSERT, UPDATE, DELETE without RETURNING
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def save_connection(connection_data: Dict) -> bool:
        """
        Save a connection configuration to the internal database.
        
        Args:
            connection_data: Dictionary with connection details
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = InternalDB.get_connection()
            cursor = conn.cursor()
            
            # Build config JSON from connection data
            config = {
                'host': connection_data.get('host'),
                'port': connection_data.get('port', 5432),
                'database': connection_data.get('database'),
                'username': connection_data.get('username'),
                'password': connection_data.get('password'),
                'schema_name': connection_data.get('schema_name', 'public')
            }
            
            # Insert or update connection using actual table schema
            cursor.execute("""
                INSERT INTO connections (
                    id, name, description, type, config, is_active, created_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, true, NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    type = EXCLUDED.type,
                    config = EXCLUDED.config,
                    updated_at = NOW()
            """, (
                connection_data['id'],
                connection_data['name'],
                connection_data.get('description', ''),
                connection_data.get('type', 'postgresql'),
                json.dumps(config)
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Connection '{connection_data['id']}' saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save connection: {e}")
            return False
    
    @staticmethod
    def load_connections() -> List[Dict]:
        """
        Load all active connections from the internal database.
        
        Returns:
            List of connection dictionaries
        """
        try:
            conn = InternalDB.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, name, description, type, config, 
                    is_active, created_at, updated_at
                FROM connections
                WHERE is_active = true
                ORDER BY created_at DESC
            """)
            
            connections = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert to list of dicts with flattened config
            result = []
            for row in connections:
                row_dict = dict(row)
                # Flatten config JSONB into the result
                config = row_dict.pop('config', {}) or {}
                row_dict['host'] = config.get('host')
                row_dict['port'] = config.get('port', 5432)
                row_dict['database'] = config.get('database')
                row_dict['username'] = config.get('username')
                row_dict['password'] = config.get('password')
                row_dict['schema_name'] = config.get('schema_name', 'public')
                result.append(row_dict)
            
            logger.info(f"Loaded {len(result)} connections from database")
            return result
            
        except Exception as e:
            logger.error(f"Failed to load connections: {e}")
            return []
    
    @staticmethod
    def get_connection_by_id(connection_id: str) -> Optional[Dict]:
        """
        Get a specific connection by ID.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Connection dictionary or None
        """
        try:
            conn = InternalDB.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, name, description, type, config, is_active
                FROM connections
                WHERE id = %s
            """, (connection_id,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not result:
                return None
            
            # Flatten config into the result
            row_dict = dict(result)
            config = row_dict.pop('config', {}) or {}
            row_dict['host'] = config.get('host')
            row_dict['port'] = config.get('port', 5432)
            row_dict['database'] = config.get('database')
            row_dict['username'] = config.get('username')
            row_dict['password'] = config.get('password')
            row_dict['schema_name'] = config.get('schema_name', 'public')
            
            return row_dict
            
        except Exception as e:
            logger.error(f"Failed to get connection {connection_id}: {e}")
            return None
    
    @staticmethod
    def update_connection_stats(connection_id: str, table_count: int = 0, 
                               relationship_count: int = 0) -> bool:
        """
        Update connection statistics after schema discovery.
        Note: Stats are stored in the config JSONB field.
        
        Args:
            connection_id: Connection identifier
            table_count: Number of discovered tables
            relationship_count: Number of discovered relationships
            
        Returns:
            True if successful
        """
        try:
            conn = InternalDB.get_connection()
            cursor = conn.cursor()
            
            # Update stats in the config JSONB field
            cursor.execute("""
                UPDATE connections
                SET 
                    config = config || %s::jsonb,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                json.dumps({
                    'table_count': table_count,
                    'relationship_count': relationship_count,
                    'last_discovered': datetime.now().isoformat()
                }),
                connection_id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update connection stats: {e}")
            return False
