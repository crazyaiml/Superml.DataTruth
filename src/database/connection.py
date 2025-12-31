"""
PostgreSQL Connection Pool Manager

Manages database connections with pooling for performance and reliability.
"""

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, Optional
from urllib.parse import quote_plus

import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection as Connection

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ConnectionPool:
    """PostgreSQL connection pool manager."""

    def __init__(
        self,
        min_connections: int = 1,
        max_connections: int = 10,
        database_url: Optional[str] = None,
    ) -> None:
        """
        Initialize connection pool.

        Args:
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            database_url: PostgreSQL connection URL (defaults to settings)
        """
        self.settings = get_settings()
        self.database_url = database_url or self._build_connection_string()
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._initialized = False

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from settings with URL-encoded password."""
        # URL-encode the password to handle special characters like @, /, etc.
        encoded_password = quote_plus(self.settings.postgres_password)
        return (
            f"postgresql://{self.settings.postgres_user}:{encoded_password}"
            f"@{self.settings.postgres_host}:{self.settings.postgres_port}/{self.settings.postgres_db}"
        )

    def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            logger.warning("Connection pool already initialized")
            return

        try:
            self._pool = pool.SimpleConnectionPool(
                self.min_connections,
                self.max_connections,
                self.database_url,
            )
            self._initialized = True
            logger.info(
                f"Connection pool initialized (min={self.min_connections}, "
                f"max={self.max_connections})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    def get_connection(self) -> Connection:
        """
        Get a connection from the pool.

        Returns:
            Database connection

        Raises:
            RuntimeError: If pool not initialized
            psycopg2.Error: If unable to get connection
        """
        if not self._initialized or not self._pool:
            raise RuntimeError(
                "Connection pool not initialized. Call initialize() first."
            )

        try:
            conn = self._pool.getconn()
            logger.debug("Connection acquired from pool")
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            raise

    def return_connection(self, conn: Connection) -> None:
        """
        Return a connection to the pool.

        Args:
            conn: Connection to return
        """
        if not self._pool:
            logger.warning("Cannot return connection - pool not initialized")
            return

        try:
            self._pool.putconn(conn)
            logger.debug("Connection returned to pool")
        except Exception as e:
            logger.error(f"Failed to return connection: {e}")

    @contextmanager
    def connection(self) -> Generator[Connection, None, None]:
        """
        Context manager for database connections.

        Yields:
            Database connection

        Example:
            with pool.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._initialized = False
            logger.info("All connections closed")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        if hasattr(self, '_pool'):
            self.close_all()


# Global connection pool singleton
_connection_pool: Optional[ConnectionPool] = None


@lru_cache(maxsize=1)
def get_connection_pool() -> ConnectionPool:
    """
    Get or create the global connection pool.

    Returns:
        Initialized ConnectionPool instance
    """
    global _connection_pool

    if _connection_pool is None:
        _connection_pool = ConnectionPool()
        _connection_pool.initialize()

    return _connection_pool
