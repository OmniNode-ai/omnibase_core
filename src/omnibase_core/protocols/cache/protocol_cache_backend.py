"""
ProtocolCacheBackend - Protocol for distributed cache backends.

This protocol defines the async interface for L2 (distributed) cache backends
that can be used with MixinCaching. Implementations may include Redis, Memcached,
Valkey, or other distributed caching solutions.

Design:
    This protocol uses async methods to support non-blocking I/O with distributed
    cache systems. All operations should be implemented with proper error handling
    and connection pooling for production use.

Architecture:
    MixinCaching uses a two-tier caching strategy:
    - L1: In-memory cache (fast, local, no network overhead)
    - L2: Distributed cache via ProtocolCacheBackend (shared across instances)

    Read path: L1 -> L2 (populate L1 on L2 hit)
    Write path: Write to both L1 and L2
    Invalidation: Remove from both L1 and L2

Usage:
    .. code-block:: python

        from omnibase_core.protocols.cache import ProtocolCacheBackend

        class RedisBackend:
            '''Redis-backed cache implementation.'''

            async def get(self, key: str) -> Any | None:
                data = await self._redis.get(key)
                return json.loads(data) if data else None

            async def set(
                self, key: str, value: Any, ttl_seconds: int | None = None
            ) -> None:
                data = json.dumps(value)
                if ttl_seconds:
                    await self._redis.setex(key, ttl_seconds, data)
                else:
                    await self._redis.set(key, data)

            async def delete(self, key: str) -> None:
                await self._redis.delete(key)

            async def clear(self) -> None:
                await self._redis.flushdb()

            async def exists(self, key: str) -> bool:
                return await self._redis.exists(key) > 0

        # Use with MixinCaching
        class MyNode(NodeCompute, MixinCaching):
            def __init__(self, container, backend: ProtocolCacheBackend):
                super().__init__(container, backend=backend)

Related:
    - OMN-1188: Redis/Valkey L2 backend for MixinCaching
    - MixinCaching: Consumer of this protocol
    - BackendCacheRedis: Default Redis implementation

.. versionadded:: 0.5.0
"""

from __future__ import annotations

__all__ = ["ProtocolCacheBackend"]

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolCacheBackend(Protocol):
    """
    Protocol for async distributed cache backends.

    Defines the interface for L2 (distributed) caching that can be used with
    MixinCaching. Implementations should handle serialization internally and
    provide proper connection management.

    Thread Safety:
        Implementations should be safe for concurrent async access.
        Most Redis/Valkey clients handle this via connection pooling.

    Error Handling:
        Implementations should handle transient errors gracefully.
        MixinCaching will fall back to L1 cache if L2 operations fail.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.cache import ProtocolCacheBackend

            class MemcachedBackend:
                '''Memcached-backed cache implementation.'''

                async def get(self, key: str) -> Any | None:
                    return await self._client.get(key)

                async def set(
                    self, key: str, value: Any, ttl_seconds: int | None = None
                ) -> None:
                    await self._client.set(key, value, exptime=ttl_seconds or 0)

                async def delete(self, key: str) -> None:
                    await self._client.delete(key)

                async def clear(self) -> None:
                    await self._client.flush_all()

                async def exists(self, key: str) -> bool:
                    return await self._client.get(key) is not None

            # Verify protocol compliance
            backend: ProtocolCacheBackend = MemcachedBackend()
            assert isinstance(backend, ProtocolCacheBackend)

    .. versionadded:: 0.5.0
    """

    async def get(self, key: str) -> Any | None:
        """
        Get cached value by key.

        Args:
            key: Cache key to retrieve.

        Returns:
            Cached value if found and not expired, None otherwise.
            Implementations should handle deserialization internally.

        Raises:
            Should not raise exceptions - return None on any error
            to allow graceful fallback to L1 cache.

        Example:
            .. code-block:: python

                result = await backend.get("user:123:profile")
                if result is not None:
                    return result  # Cache hit
        """
        ...

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Store value in cache with optional TTL.

        Args:
            key: Cache key to store under.
            value: Value to cache. Should be serializable (implementations
                handle serialization internally).
            ttl_seconds: Time-to-live in seconds. If None, the entry
                may live indefinitely or use a backend-specific default.
                If 0 or negative, implementations should skip caching
                (return immediately without storing).

        Note:
            Zero or negative TTL values should be treated as "do not cache".
            Implementations should return immediately without storing to prevent
            storing entries that would expire immediately or have invalid TTLs.

        Raises:
            Should not raise exceptions - silently fail to allow
            graceful degradation.

        Example:
            .. code-block:: python

                # Store with 5 minute TTL
                await backend.set("user:123:profile", profile_data, ttl_seconds=300)

                # Store with no expiration
                await backend.set("config:global", config_data)

                # Skip caching (ttl=0)
                await backend.set("temp:data", data, ttl_seconds=0)  # No-op
        """
        ...

    async def delete(self, key: str) -> None:
        """
        Delete a cache entry.

        Args:
            key: Cache key to delete.

        Note:
            Should succeed silently if key does not exist.
            Should not raise exceptions.

        Example:
            .. code-block:: python

                await backend.delete("user:123:profile")
        """
        ...

    async def clear(self) -> None:
        """
        Clear all cache entries.

        Warning:
            This operation may be expensive for large caches.
            Use sparingly in production.

        Note:
            Should not raise exceptions.
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key to check.

        Returns:
            True if key exists and is not expired, False otherwise.
            Returns False on any error to allow graceful fallback.

        Example:
            .. code-block:: python

                if await backend.exists("user:123:profile"):
                    # Key exists, safe to get
                    data = await backend.get("user:123:profile")
        """
        ...
