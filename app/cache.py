"""
Redis caching utilities for Tatuzinho project.

This module provides a CacheManager class that wraps Redis operations and provides
decorator-based caching for functions. Cache is automatically invalidated when
data is mutated.
"""

import json
import logging
from typing import Optional, TypeVar, Callable, Any, Dict, List
import functools
from redis import Redis

# Type variable for generic caching
T = TypeVar("T")

logger = logging.getLogger(__name__)


class CacheManager:
    """Manager for Redis-based caching operations.
    
    Provides methods to cache function results, invalidate cached data,
    and handle graceful cache failures. All cache operations are logged
    for observability.
    
    Args:
        redis_client: Redis client instance for cache operations.
    """
    
    def __init__(self, redis_client: Redis) -> None:
        """Initialize CacheManager with Redis client.
        
        Args:
            redis_client: Initialized Redis connection.
        """
        self.redis = redis_client
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.
        
        Args:
            key: Cache key to retrieve.
        
        Returns:
            Cached value if found and valid, None otherwise.
        """
        try:
            cached = self.redis.get(key)
            if cached:
                logger.debug(f"Cache hit", extra={"cache_key": key})
                return json.loads(cached)
            logger.debug(f"Cache miss", extra={"cache_key": key})
            return None
        except Exception as e:
            logger.warning(
                f"Cache read error",
                extra={"cache_key": key, "error": str(e)},
            )
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> bool:
        """Set a value in cache.
        
        Args:
            key: Cache key to set.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds (default: 1 hour).
        
        Returns:
            True if successfully cached, False if cache operation failed.
        """
        try:
            self.redis.setex(
                key,
                ttl,
                json.dumps(value, default=str),
            )
            logger.debug(
                f"Cache set",
                extra={"cache_key": key, "ttl_seconds": ttl},
            )
            return True
        except Exception as e:
            logger.warning(
                f"Cache write error",
                extra={"cache_key": key, "error": str(e)},
            )
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value from cache.
        
        Args:
            key: Cache key to delete.
        
        Returns:
            True if key existed and was deleted, False otherwise.
        """
        try:
            deleted = self.redis.delete(key) > 0
            if deleted:
                logger.debug(f"Cache invalidated", extra={"cache_key": key})
            return deleted
        except Exception as e:
            logger.warning(
                f"Cache delete error",
                extra={"cache_key": key, "error": str(e)},
            )
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache keys matching a pattern.
        
        Use hierarchical cache keys for easy pattern invalidation:
        - standings:tournament:1:*
        - top_scorers:tournament:1
        - matches:tournament:1:*
        
        Args:
            pattern: Redis glob pattern (e.g., 'standings:tournament:1:*').
        
        Returns:
            Number of keys deleted.
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(
                    f"Cache invalidated by pattern",
                    extra={"pattern": pattern, "keys_deleted": deleted},
                )
                return deleted
            return 0
        except Exception as e:
            logger.warning(
                f"Cache invalidation error",
                extra={"pattern": pattern, "error": str(e)},
            )
            return 0
    
    def invalidate_multiple(self, keys: List[str]) -> int:
        """Invalidate multiple cache keys.
        
        Args:
            keys: List of cache keys to delete.
        
        Returns:
            Number of keys deleted.
        """
        if not keys:
            return 0
        
        try:
            deleted = self.redis.delete(*keys)
            logger.info(
                f"Multiple cache keys invalidated",
                extra={"keys_count": len(keys), "deleted": deleted},
            )
            return deleted
        except Exception as e:
            logger.warning(
                f"Bulk cache invalidation error",
                extra={"keys_count": len(keys), "error": str(e)},
            )
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache (use with caution!).
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            self.redis.flushdb()
            logger.warning("All cache cleared")
            return True
        except Exception as e:
            logger.error(
                f"Cache clear error",
                extra={"error": str(e)},
            )
            return False
    
    def cache(
        self,
        key: str,
        ttl: int = 3600,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator for caching function results.
        
        Caches the return value of a function with the given key and TTL.
        If cache misses or fails, the function is called and result is cached.
        Cache failures are logged but do not block function execution.
        
        Args:
            key: Cache key (use hierarchical naming: 'resource:type:id:filter').
            ttl: Time-to-live in seconds (default: 1 hour).
        
        Returns:
            Decorator function.
        
        Example:
            >>> @cache_manager.cache('top_scorers:tournament:1', ttl=3600)
            ... def get_top_scorers(tournament_id: int) -> List[Player]:
            ...     return db.query(Player).join(...).limit(10).all()
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                # Try to get from cache
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value
                
                # Call function if cache miss
                result = func(*args, **kwargs)
                
                # Cache the result
                self.set(key, result, ttl)
                
                return result
            
            return wrapper
        
        return decorator
    
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy.
        
        Returns:
            True if Redis is reachable and responding, False otherwise.
        """
        try:
            self.redis.ping()
            return True
        except Exception as e:
            logger.warning(
                f"Redis health check failed",
                extra={"error": str(e)},
            )
            return False
