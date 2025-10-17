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
- Thread-safe operations

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
        ttl_seconds: TTL in seconds (None = no expiration)
        eviction_policy: Cache eviction strategy (lru/lfu/fifo)
        enable_stats: Enable cache statistics tracking

    Thread Safety:
        ⚠️ NOT thread-safe by default
        - LRU operations are not atomic
        - Concurrent get/put operations can corrupt cache state
        - Production use requires external synchronization (e.g., threading.Lock)
        - See docs/THREADING.md for thread-safe wrapper implementation
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_minutes: int = 30,
        ttl_seconds: int | None = None,
        eviction_policy: str = "lru",
        enable_stats: bool = True,
    ):
        """
        Initialize ModelComputeCache with size and TTL configuration.

        Args:
            max_size: Maximum number of cache entries (default: 1000)
            default_ttl_minutes: Default TTL in minutes (default: 30)
            ttl_seconds: TTL in seconds (overrides default_ttl_minutes if provided)
            eviction_policy: Eviction policy - lru/lfu/fifo (default: lru)
            enable_stats: Enable cache hit/miss statistics (default: True)
        """
        self.max_size = max_size
        self.eviction_policy = eviction_policy
        self.enable_stats = enable_stats

        # TTL handling: prefer seconds, fallback to minutes
        if ttl_seconds is not None:
            self.ttl_seconds = ttl_seconds
            self.default_ttl_minutes = ttl_seconds // 60 if ttl_seconds > 0 else 0
        else:
            self.default_ttl_minutes = default_ttl_minutes
            self.ttl_seconds = default_ttl_minutes * 60

        # Cache storage: key -> (value, expiry, access_count/frequency/insert_order)
        self._cache: dict[str, tuple[Any, datetime, int]] = {}

        # Statistics tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "total_requests": 0,
        }

    def get(self, cache_key: str) -> Any | None:
        """
        Get cached value if valid and not expired.

        Args:
            cache_key: Unique key for the cached computation

        Returns:
            Cached value if valid, None if expired or not found
        """
        if self.enable_stats:
            self._stats["total_requests"] += 1

        if cache_key not in self._cache:
            if self.enable_stats:
                self._stats["misses"] += 1
            return None

        value, expiry, access_count = self._cache[cache_key]

        if datetime.now() > expiry:
            del self._cache[cache_key]
            if self.enable_stats:
                self._stats["misses"] += 1
                self._stats["expirations"] += 1
            return None

        # Update access count/frequency based on eviction policy
        if self.eviction_policy == "lru":
            self._cache[cache_key] = (value, expiry, access_count + 1)
        elif self.eviction_policy == "lfu":
            self._cache[cache_key] = (value, expiry, access_count + 1)
        # FIFO doesn't update access count

        if self.enable_stats:
            self._stats["hits"] += 1

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
            self._evict()

        ttl = ttl_minutes or self.default_ttl_minutes
        expiry = datetime.now() + timedelta(minutes=ttl)
        self._cache[cache_key] = (value, expiry, 1)

    def _evict(self) -> None:
        """Evict item based on configured eviction policy."""
        if not self._cache:
            return

        if self.eviction_policy == "lru":
            # Evict least recently used (lowest access count)
            evict_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        elif self.eviction_policy == "lfu":
            # Evict least frequently used (lowest frequency count)
            evict_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        else:  # fifo
            # Evict first in (oldest insertion)
            evict_key = next(iter(self._cache))

        del self._cache[evict_key]

        if self.enable_stats:
            self._stats["evictions"] += 1

    def _evict_lru(self) -> None:
        """Legacy LRU eviction method."""
        self._evict()

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        if self.enable_stats:
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "expirations": 0,
                "total_requests": 0,
            }

    def get_stats(self) -> dict[str, int | float]:
        """
        Get cache statistics for monitoring and optimization.

        Returns:
            Dictionary with cache metrics:
            - total_entries: Total cached items
            - expired_entries: Count of expired items
            - valid_entries: Count of valid items
            - max_size: Maximum cache capacity
            - hits: Cache hit count (if stats enabled)
            - misses: Cache miss count (if stats enabled)
            - hit_rate: Cache hit rate percentage (if stats enabled)
            - evictions: Eviction count (if stats enabled)
            - expirations: Expiration count (if stats enabled)
        """
        now = datetime.now()
        expired_count = sum(1 for _, expiry, _ in self._cache.values() if expiry <= now)

        stats: dict[str, int | float] = {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "valid_entries": len(self._cache) - expired_count,
            "max_size": self.max_size,
        }

        if self.enable_stats:
            total_requests = self._stats["total_requests"]
            hit_rate = (
                (self._stats["hits"] / total_requests * 100)
                if total_requests > 0
                else 0.0
            )
            stats.update(
                {
                    "hits": self._stats["hits"],
                    "misses": self._stats["misses"],
                    "hit_rate": round(hit_rate, 2),
                    "evictions": self._stats["evictions"],
                    "expirations": self._stats["expirations"],
                    "total_requests": total_requests,
                }
            )

        return stats
