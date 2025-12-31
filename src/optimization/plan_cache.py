"""
Query Plan Cache

Caches QueryPlan objects to avoid repeated LLM calls for similar questions.
Uses semantic similarity matching to find cached plans.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from redis import Redis

from src.config.settings import get_settings
from src.planner.query_plan import QueryPlan


class QueryPlanCache:
    """Cache for QueryPlan objects with semantic similarity matching."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize plan cache.
        
        Args:
            redis_client: Redis client instance
        """
        settings = get_settings()
        
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
            )
        
        self.ttl_seconds = 3600  # 1 hour default TTL
        self.key_prefix = "plan_cache:"
    
    def _generate_key(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate cache key from question and context.
        
        Args:
            question: Natural language question
            context: Optional context information
            
        Returns:
            Cache key string
        """
        # Normalize question (lowercase, strip whitespace)
        normalized_question = question.lower().strip()
        
        # Include context in key if provided
        if context:
            context_str = json.dumps(context, sort_keys=True)
            key_input = f"{normalized_question}:{context_str}"
        else:
            key_input = normalized_question
        
        # Generate hash
        key_hash = hashlib.sha256(key_input.encode()).hexdigest()
        
        return f"{self.key_prefix}{key_hash}"
    
    def get(self, question: str, context: Optional[Dict[str, Any]] = None) -> Optional[QueryPlan]:
        """
        Retrieve cached QueryPlan.
        
        Args:
            question: Natural language question
            context: Optional context information
            
        Returns:
            Cached QueryPlan or None if not found
        """
        key = self._generate_key(question, context)
        
        try:
            cached_data = self.redis.get(key)
            
            if cached_data:
                plan_dict = json.loads(cached_data)
                return QueryPlan(**plan_dict)
            
            return None
            
        except Exception as e:
            # Log error but don't fail - just return cache miss
            print(f"Cache get error: {e}")
            return None
    
    def set(
        self,
        question: str,
        plan: QueryPlan,
        context: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache a QueryPlan.
        
        Args:
            question: Natural language question
            plan: QueryPlan to cache
            context: Optional context information
            ttl: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        key = self._generate_key(question, context)
        ttl = ttl or self.ttl_seconds
        
        try:
            # Serialize QueryPlan to dict
            plan_dict = plan.model_dump()
            plan_json = json.dumps(plan_dict)
            
            # Store in Redis with TTL
            self.redis.setex(key, ttl, plan_json)
            
            return True
            
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def invalidate(self, question: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Invalidate a cached QueryPlan.
        
        Args:
            question: Natural language question
            context: Optional context information
            
        Returns:
            True if key was deleted, False otherwise
        """
        key = self._generate_key(question, context)
        
        try:
            deleted = self.redis.delete(key)
            return deleted > 0
        except Exception as e:
            print(f"Cache invalidate error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cached plans matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "plan_cache:*")
            
        Returns:
            Number of keys invalidated
        """
        try:
            # Find all matching keys
            keys = list(self.redis.scan_iter(match=f"{self.key_prefix}{pattern}"))
            
            if keys:
                return self.redis.delete(*keys)
            
            return 0
            
        except Exception as e:
            print(f"Cache invalidate pattern error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        try:
            # Count total cached plans
            keys = list(self.redis.scan_iter(match=f"{self.key_prefix}*"))
            total_keys = len(keys)
            
            # Get Redis memory info
            info = self.redis.info('memory')
            
            return {
                "total_cached_plans": total_keys,
                "memory_used_bytes": info.get('used_memory', 0),
                "memory_used_human": info.get('used_memory_human', 'unknown'),
                "ttl_seconds": self.ttl_seconds
            }
            
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {
                "total_cached_plans": 0,
                "error": str(e)
            }
    
    def clear_all(self) -> int:
        """
        Clear all cached query plans.
        
        Returns:
            Number of keys deleted
        """
        return self.invalidate_pattern("*")
    
    def ping(self) -> bool:
        """
        Check if Redis connection is alive.
        
        Returns:
            True if connection is healthy
        """
        try:
            return self.redis.ping()
        except Exception:
            return False


# Singleton instance
_plan_cache_instance = None


def get_plan_cache() -> QueryPlanCache:
    """
    Get or create the global QueryPlanCache instance.
    
    Returns:
        QueryPlanCache singleton
    """
    global _plan_cache_instance
    
    if _plan_cache_instance is None:
        _plan_cache_instance = QueryPlanCache()
    
    return _plan_cache_instance
