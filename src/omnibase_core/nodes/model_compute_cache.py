"""
VERSION: 1.0.0
STABILITY GUARANTEE: Abstract method signatures frozen.
Breaking changes require major version bump.

ModelComputeCache - Caching Layer for Compute Node Operations.

Provides TTL-based caching with memory management and LRU eviction for expensive
computational operations. Designed for use with NodeCompute to optimize performance
through intelligent result caching.

Key Capabilities:
- TTL-based cache expiration
- LRU eviction policy for memory management
- Access count tracking
- Cache statistics and monitoring

STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.
Code generators can target this stable interface.

Author: ONEX Framework Team
"""

from datetime import datetime, timedelta
from typing import Any

__all__ = ["ModelComputeCache"]


class ModelComputeCache:
    """
    Caching layer for expensive computations with TTL and memory management.

    Provides intelligent caching with time-to-live (TTL) expiration and
    least-recently-used (LRU) eviction to optimize compute-intensive operations.

    Attributes:
        max_size: Maximum number of cache entries
        default_ttl_minutes: Default TTL in minutes for cached values
    """

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        """
        Initialize ModelComputeCache with size and TTL configuration.

        Args:
            max_size: Maximum number of cache entries (default: 1000)
            default_ttl_minutes: Default TTL in minutes (default: 30)
        """
        self.max_size = max_size
        self.default_ttl_minutes = default_ttl_minutes
        self._cache: dict[str, tuple[Any, datetime, int]] = {}

    def get(self, cache_key: str) -> Any | None:
        """
        Get cached value if valid and not expired.

        Args:
            cache_key: Unique key for the cached computation

        Returns:
            Cached value if valid, None if expired or not found
        """
        if cache_key not in self._cache:
            return None

        value, expiry, access_count = self._cache[cache_key]

        if datetime.now() > expiry:
            del self._cache[cache_key]
            return None

        self._cache[cache_key] = (value, expiry, access_count + 1)
        return value

    def put(self, cache_key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """
        Cache value with TTL.

        Args:
            cache_key: Unique key for the computation
            value: Result to cache
            ttl_minutes: Custom TTL in minutes (uses default if None)
        """
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        ttl = ttl_minutes or self.default_ttl_minutes
        expiry = datetime.now() + timedelta(minutes=ttl)
        self._cache[cache_key] = (value, expiry, 1)

    def _evict_lru(self) -> None:
        """Evict least recently used item based on access count."""
        if not self._cache:
            return

        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        del self._cache[lru_key]

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics for monitoring and optimization.

        Returns:
            Dictionary with cache metrics:
            - total_entries: Total cached items
            - expired_entries: Count of expired items
            - valid_entries: Count of valid items
            - max_size: Maximum cache capacity
        """
        now = datetime.now()
        expired_count = sum(1 for _, expiry, _ in self._cache.values() if expiry <= now)

        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "valid_entries": len(self._cache) - expired_count,
            "max_size": self.max_size,
        }
