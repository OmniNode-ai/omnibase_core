"""
ProtocolComputeCache - Protocol for computation result caching.

This protocol defines the interface for caching computation results in NodeCompute.
By using a protocol instead of direct implementation, NodeCompute can remain pure
while caching logic is handled by infrastructure layer implementations.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations (ModelComputeCache or custom caches) satisfy the contract.
    This allows NodeCompute to be pure computation with optional caching.

Architecture:
    NodeCompute receives an optional cache via container. If provided, the cache
    is used for result storage and retrieval. If not provided, NodeCompute operates
    without caching (pure mode).

Usage:
    .. code-block:: python

        from omnibase_core.protocols.compute import ProtocolComputeCache

        class InMemoryCache(ProtocolComputeCache):
            def get(self, cache_key: str) -> Any | None:
                return self._cache.get(cache_key)

            def put(self, cache_key: str, value: Any, ttl_minutes: int | None = None) -> None:
                self._cache[cache_key] = value

            def clear(self) -> None:
                self._cache.clear()

            def get_stats(self) -> dict[str, int | float]:
                return {"total_entries": len(self._cache)}

        # Use in NodeCompute
        node = NodeCompute(container)
        # If container provides ProtocolComputeCache, caching is enabled

Related:
    - OMN-700: Fix NodeCompute Purity Violations
    - ModelComputeCache: Default implementation of this protocol
    - NodeCompute: Consumer of this protocol

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ProtocolComputeCache"]

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolComputeCache(Protocol):
    """
    Protocol for computation result caching.

    Defines the interface for caching computed results with TTL-based
    expiration and statistics tracking. Implementations may provide
    different eviction policies (LRU, LFU, FIFO) and storage backends.

    Thread Safety:
        WARNING: Implementations are NOT guaranteed to be thread-safe.
        If using in multi-threaded contexts, implementations should
        either be thread-safe internally or callers should use
        external synchronization.

        Design Requirements:
            - **Thread-Safe Implementations**: Use internal locking if the
              cache will be shared across threads.
            - **Single-Threaded Use**: If each thread has its own cache
              instance, no synchronization is needed.

    Attributes:
        max_size: Maximum number of cache entries (implementation-specific)
        eviction_policy: Cache eviction strategy (implementation-specific)

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolComputeCache

            class RedisCache:
                '''Redis-backed cache implementation.'''

                def get(self, cache_key: str) -> Any | None:
                    data = self._redis.get(cache_key)
                    return pickle.loads(data) if data else None

                def put(
                    self, cache_key: str, value: Any, ttl_minutes: int | None = None
                ) -> None:
                    ttl_seconds = (ttl_minutes or 30) * 60
                    self._redis.setex(cache_key, ttl_seconds, pickle.dumps(value))

                def clear(self) -> None:
                    self._redis.flushdb()

                def get_stats(self) -> dict[str, int | float]:
                    info = self._redis.info()
                    return {
                        "total_entries": info["db0"]["keys"],
                        "hits": info["keyspace_hits"],
                        "misses": info["keyspace_misses"],
                    }

            # Verify protocol compliance
            cache: ProtocolComputeCache = RedisCache()
            assert isinstance(cache, ProtocolComputeCache)

    .. versionadded:: 0.4.0
    """

    def get(self, cache_key: str) -> Any | None:
        """
        Get cached value if valid and not expired.

        Args:
            cache_key: Unique key for the cached computation.
                Keys should be deterministically generated from
                computation inputs.

        Returns:
            Cached value if valid and not expired, None otherwise.
            Implementations should handle expiration internally and
            return None for expired entries.

        Example:
            .. code-block:: python

                result = cache.get("sum_numbers:abc123")
                if result is not None:
                    return result  # Cache hit
                # Cache miss - compute and store
        """
        ...

    def put(self, cache_key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """
        Cache value with optional TTL.

        Args:
            cache_key: Unique key for the computation.
                Keys should be deterministically generated from
                computation inputs.
            value: Result to cache. Should be serializable if using
                distributed cache backends.
            ttl_minutes: Custom TTL in minutes. If None, uses the
                cache's default TTL configuration.

        Note:
            Implementations should handle eviction if the cache is full.
            The eviction policy (LRU, LFU, FIFO) is implementation-specific.

        Example:
            .. code-block:: python

                # Cache with default TTL
                cache.put("sum_numbers:abc123", 15.0)

                # Cache with custom TTL (1 hour)
                cache.put("expensive_computation:xyz", result, ttl_minutes=60)
        """
        ...

    def clear(self) -> None:
        """
        Clear all cached values.

        This should remove all entries from the cache and reset
        statistics if applicable.

        Note:
            This operation may be expensive for large caches or
            distributed backends. Use sparingly.
        """
        ...

    def get_stats(self) -> dict[str, int | float]:
        """
        Get cache statistics for monitoring and optimization.

        Returns:
            Dictionary with cache metrics. Common keys include:
            - total_entries: Total cached items
            - valid_entries: Count of non-expired items
            - max_size: Maximum cache capacity
            - hits: Cache hit count (if stats enabled)
            - misses: Cache miss count (if stats enabled)
            - hit_rate: Cache hit rate percentage (if stats enabled)
            - evictions: Eviction count (if stats enabled)

        Example:
            .. code-block:: python

                stats = cache.get_stats()
                if stats.get("hit_rate", 0) < 50:
                    # Consider increasing cache size or TTL
                    log.warning(f"Low cache hit rate: {stats['hit_rate']}%")
        """
        ...
