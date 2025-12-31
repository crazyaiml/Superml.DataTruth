"""
Query Cache with Redis

Caches query results for improved performance.
"""

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import redis

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class QueryCache:
    """Redis-based query result cache."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,  # 1 hour
        enabled: bool = True,
    ) -> None:
        """
        Initialize query cache.

        Args:
            redis_url: Redis connection URL (defaults to settings)
            default_ttl: Default TTL in seconds for cached results
            enabled: Whether caching is enabled
        """
        self.settings = get_settings()
        self.redis_url = redis_url or self._build_redis_url()
        self.default_ttl = default_ttl
        self.enabled = enabled
        self._client: Optional[redis.Redis] = None
        self._initialized = False

    def _build_redis_url(self) -> str:
        """Build Redis connection URL from settings."""
        return f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"

    def initialize(self) -> None:
        """Initialize Redis connection."""
        if not self.enabled:
            logger.info("Query cache disabled")
            return

        if self._initialized:
            logger.warning("Query cache already initialized")
            return

        try:
            self._client = redis.from_url(
                self.redis_url, decode_responses=True, socket_timeout=5
            )
            # Test connection
            self._client.ping()
            self._initialized = True
            logger.info("Query cache initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize query cache: {e}. Caching disabled.")
            self.enabled = False

    def _generate_key(self, sql: str) -> str:
        """
        Generate cache key from SQL query.

        Args:
            sql: SQL query string

        Returns:
            Cache key (hash of normalized SQL)
        """
        # Normalize SQL (lowercase, remove extra whitespace)
        normalized = " ".join(sql.lower().split())
        # Generate SHA256 hash
        return f"query:{hashlib.sha256(normalized.encode()).hexdigest()}"

    def get(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached query result.

        Args:
            sql: SQL query string

        Returns:
            Cached result or None if not found
        """
        if not self.enabled or not self._client:
            return None

        try:
            key = self._generate_key(sql)
            cached_data = self._client.get(key)

            if cached_data:
                logger.debug(f"Cache HIT for query: {sql[:100]}...")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache MISS for query: {sql[:100]}...")
                return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(
        self, sql: str, result: List[Dict[str, Any]], ttl: Optional[int] = None
    ) -> None:
        """
        Cache query result.

        Args:
            sql: SQL query string
            result: Query result to cache
            ttl: Time-to-live in seconds (defaults to default_ttl)
        """
        if not self.enabled or not self._client:
            return

        try:
            key = self._generate_key(sql)
            ttl = ttl or self.default_ttl
            self._client.setex(key, ttl, json.dumps(result))
            logger.debug(f"Cached query result (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def invalidate(self, pattern: str = "query:*") -> int:
        """
        Invalidate cached queries matching pattern.

        Args:
            pattern: Redis key pattern (default: all queries)

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self._client:
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                deleted = self._client.delete(*keys)
                logger.info(f"Invalidated {deleted} cached queries")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._initialized = False
            logger.info("Query cache closed")


# Global cache singleton
_query_cache: Optional[QueryCache] = None


@lru_cache(maxsize=1)
def get_query_cache() -> QueryCache:
    """
    Get or create the global query cache.

    Returns:
        Initialized QueryCache instance
    """
    global _query_cache

    if _query_cache is None:
        _query_cache = QueryCache()
        _query_cache.initialize()

    return _query_cache
