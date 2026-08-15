"""
Caching system for the ATS Resume Analyzer API.
Provides in-memory caching with TTL support for NLP models and frequent queries.
"""
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger('ats_resume_scorer')


class TTLCache:
    """
    Thread-safe in-memory cache with Time-To-Live (TTL) support.
    Automatically evicts expired entries on access.
    """
    
    def __init__(self, default_ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize the cache.
        
        Args:
            default_ttl_seconds: Default time-to-live for cached items (5 minutes)
            max_size: Maximum number of items in the cache
        """
        self._default_ttl = default_ttl_seconds
        self._max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)
        self._access_count: Dict[str, int] = {}  # key -> access count (for LRU eviction)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        Returns None if key doesn't exist or has expired.
        
        Args:
            key: Cache key string
            
        Returns:
            Cached value or None if miss/expired
        """
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        
        # Check if expired
        if time.time() > expiry:
            del self._cache[key]
            self._access_count.pop(key, None)
            return None
        
        # Track access for LRU
        self._access_count[key] = self._access_count.get(key, 0) + 1
        
        return value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set a value in the cache with optional TTL.
        
        Args:
            key: Cache key string
            value: Value to cache
            ttl_seconds: Optional custom TTL (uses default if not specified)
        """
        # Evict if at max capacity
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._evict_lru()
        
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
        self._access_count[key] = 0
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed and was deleted
        """
        if key in self._cache:
            del self._cache[key]
            self._access_count.pop(key, None)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        self._access_count.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache size, max size, hit rate, etc.
        """
        now = time.time()
        active_items = sum(1 for v, e in self._cache.values() if now <= e)
        expired_items = len(self._cache) - active_items
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "active_items": active_items,
            "expired_items": expired_items,
            "default_ttl_seconds": self._default_ttl,
            "usage_percent": round((len(self._cache) / self._max_size) * 100, 1) if self._max_size > 0 else 0,
        }
    
    def _evict_lru(self) -> None:
        """Evict the least recently accessed item."""
        if not self._access_count:
            return
        
        # Find the least accessed key
        min_key = min(self._access_count, key=self._access_count.get)
        
        # Remove it
        self._cache.pop(min_key, None)
        self._access_count.pop(min_key, None)
        logger.debug(f"Evicted LRU cache key: {min_key}")


# Global cache instances
nlp_model_cache = TTLCache(default_ttl_seconds=3600, max_size=10)  # 1 hour TTL for models
analysis_cache = TTLCache(default_ttl_seconds=300, max_size=500)   # 5 min TTL for analysis results
query_cache = TTLCache(default_ttl_seconds=60, max_size=200)       # 1 min TTL for frequent queries


def cached(ttl_seconds: Optional[int] = None, cache_name: str = "analysis_cache"):
    """
    Decorator that caches function results based on arguments.
    
    Args:
        ttl_seconds: Optional custom TTL
        cache_name: Which cache to use ('analysis_cache', 'query_cache', 'nlp_model_cache')
        
    Returns:
        Decorated function with caching
    """
    caches = {
        "analysis_cache": analysis_cache,
        "query_cache": query_cache,
        "nlp_model_cache": nlp_model_cache,
    }
    
    cache = caches.get(cache_name, analysis_cache)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for: {func.__name__}")
                return cached_result
            
            # Compute result
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    
    return decorator


def invalidate_analysis_cache(pattern: Optional[str] = None) -> int:
    """
    Invalidate cached analysis results, optionally matching a pattern.
    
    Args:
        pattern: Optional string pattern to match against cache keys
        
    Returns:
        Number of items invalidated
    """
    count = 0
    if pattern:
        keys_to_delete = [k for k in analysis_cache._cache if pattern in k]
        for key in keys_to_delete:
            analysis_cache.delete(key)
            count += 1
    else:
        count = len(analysis_cache._cache)
        analysis_cache.clear()
    
    logger.info(f"Invalidated {count} cache entries")
    return count