"""TTL Cache Manager for command results (v3.0.0)"""

import time
from typing import Any, Optional, Dict, Tuple
from threading import Lock
from mcp.logging_config import get_logger

logger = get_logger(__name__)


class TTLCache:
    """Thread-safe TTL (Time-To-Live) cache with automatic expiration"""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 100):
        """Initialize TTL cache

        Args:
            ttl_seconds: Time to live for cache entries (default: 60 seconds)
            max_size: Maximum number of entries to store (default: 100)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, timestamp = self._cache[key]
            age = time.time() - timestamp

            if age > self.ttl_seconds:
                # Expired - remove from cache
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache expired: {key} (age: {age:.1f}s)")
                return None

            self._hits += 1
            logger.debug(f"Cache hit: {key} (age: {age:.1f}s)")
            return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Enforce max size (evict oldest entries)
            if len(self._cache) >= self.max_size:
                self._evict_oldest()

            self._cache[key] = (value, time.time())
            logger.debug(f"Cache set: {key}")

    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated: {key}")
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys containing pattern

        Args:
            pattern: String pattern to match in keys

        Returns:
            Number of keys invalidated
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]

            if keys_to_remove:
                logger.debug(f"Cache invalidated {len(keys_to_remove)} keys matching: {pattern}")

            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Cache cleared: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Dict with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%"
            }

    def _evict_oldest(self) -> None:
        """Evict oldest entry from cache (assumes lock is held)"""
        if not self._cache:
            return

        # Find oldest entry
        oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
        del self._cache[oldest_key]
        logger.debug(f"Cache eviction: {oldest_key} (max size reached)")


# Global cache instances for different command types
_element_search_cache = TTLCache(ttl_seconds=60, max_size=50)
_page_info_cache = TTLCache(ttl_seconds=60, max_size=20)


def get_element_search_cache() -> TTLCache:
    """Get global element search cache instance"""
    return _element_search_cache


def get_page_info_cache() -> TTLCache:
    """Get global page info cache instance"""
    return _page_info_cache
