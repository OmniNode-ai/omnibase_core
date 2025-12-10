"""
ModelComputeCache - Caching Layer for Compute Node Operations.

Provides TTL-based caching with memory management and LRU eviction for expensive
computational operations. Designed for use with NodeCompute to optimize performance
through intelligent result caching.

Key Capabilities:
- TTL-based cache expiration
- LRU eviction policy for memory management
- Access count tracking
- Cache statistics and monitoring

"""

from datetime import datetime, timedelta
from time import monotonic
from typing import Any

from omnibase_core.enums.enum_cache_eviction_policy import EnumCacheEvictionPolicy

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
        eviction_policy: EnumCacheEvictionPolicy | str = EnumCacheEvictionPolicy.LRU,
        enable_stats: bool = True,
    ):
        """
        Initialize ModelComputeCache with size and TTL configuration.

        Args:
            max_size: Maximum number of cache entries (default: 1000)
            default_ttl_minutes: Default TTL in minutes (default: 30)
            ttl_seconds: TTL in seconds (overrides default_ttl_minutes if provided)
            eviction_policy: Eviction policy - EnumCacheEvictionPolicy or "lru"/"lfu"/"fifo" (default: LRU)
            enable_stats: Enable cache hit/miss statistics (default: True)
        """
        self.max_size = max_size
        # Normalize eviction_policy to enum
        if isinstance(eviction_policy, str):
            self.eviction_policy = EnumCacheEvictionPolicy(eviction_policy)
        else:
            self.eviction_policy = eviction_policy  # type: ignore[unreachable]
        self.enable_stats = enable_stats

        # TTL handling: store as timedelta for precision
        if ttl_seconds is not None:
            self.ttl = timedelta(seconds=ttl_seconds)
            self.default_ttl_minutes = ttl_seconds // 60 if ttl_seconds > 0 else 0
        else:
            self.ttl = timedelta(minutes=default_ttl_minutes)
            self.default_ttl_minutes = default_ttl_minutes

        # Cache storage: key -> (value, expiry, last_access_time|access_count)
        # For LRU: last_access_time (float from monotonic())
        # For LFU/FIFO: access_count (int)
        self._cache: dict[str, tuple[Any, datetime, float | int]] = {}

        # FIFO insertion counter
        self._insert_order = 0

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

        value, expiry, access_metric = self._cache[cache_key]

        if datetime.now() > expiry:
            del self._cache[cache_key]
            if self.enable_stats:
                self._stats["misses"] += 1
                self._stats["expirations"] += 1
            return None

        # Update access metric based on eviction policy
        if self.eviction_policy == EnumCacheEvictionPolicy.LRU:
            # LRU: Update last access time (timestamp)
            self._cache[cache_key] = (value, expiry, monotonic())
        elif self.eviction_policy == EnumCacheEvictionPolicy.LFU:
            # LFU: Increment access count
            self._cache[cache_key] = (value, expiry, int(access_metric) + 1)
        # FIFO doesn't update access metric

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
        # Guard against invalid max_size
        if self.max_size <= 0:
            return

        if len(self._cache) >= self.max_size:
            self._evict()

        ttl = timedelta(minutes=ttl_minutes) if ttl_minutes is not None else self.ttl
        expiry = datetime.now() + ttl

        # Set initial access metric based on eviction policy
        if self.eviction_policy == EnumCacheEvictionPolicy.LRU:
            access_metric = monotonic()  # Current timestamp
        elif self.eviction_policy == EnumCacheEvictionPolicy.LFU:
            access_metric = 1  # Initial access count
        else:  # FIFO
            self._insert_order += 1
            access_metric = self._insert_order  # Insertion order

        self._cache[cache_key] = (value, expiry, access_metric)

    def _evict(self) -> None:
        """Evict item based on configured eviction policy."""
        if not self._cache:
            return

        if self.eviction_policy == EnumCacheEvictionPolicy.LRU:
            # Evict least recently used (smallest timestamp = oldest access)
            evict_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        elif self.eviction_policy == EnumCacheEvictionPolicy.LFU:
            # Evict least frequently used (lowest access count)
            evict_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        else:  # FIFO
            # Evict first in (lowest insertion order)
            evict_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])

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
