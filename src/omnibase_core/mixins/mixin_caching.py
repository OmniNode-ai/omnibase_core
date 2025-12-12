"""
MixinCaching - Result Caching Mixin

Provides result caching capabilities for ONEX nodes, particularly useful for
Compute and Reducer nodes that perform expensive operations.

This is a stub implementation - full caching with Redis/Memcached backends
to be implemented in future phases.

Usage:
    class MyComputeNode(NodeCompute, MixinCaching):
        async def execute_compute(self, contract):
            cache_key = self.generate_cache_key(contract.input_data)
            cached = await self.get_cached(cache_key)
            if cached:
                return cached

            result = await self._expensive_computation(contract)
            await self.set_cached(cache_key, result, ttl_seconds=600)
            return result
"""

import hashlib
import json
from typing import Any

from omnibase_core.types.typed_dict_mixin_types import TypedDictCacheStats


class MixinCaching:
    """
    Mixin providing result caching capabilities.

    This is a stub implementation providing the interface for caching operations.
    Full implementation with cache backends (Redis, Memcached, etc.) will be
    added in future phases.

    Attributes:
        _cache_enabled: Whether caching is enabled
        _cache_data: In-memory cache storage (stub) - stores serializable values
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize caching mixin."""
        super().__init__(*args, **kwargs)
        self._cache_enabled = True
        # Cache stores arbitrary serializable values - use object for type flexibility
        self._cache_data: dict[str, object] = {}

    def generate_cache_key(self, data: Any) -> str:
        """
        Generate a cache key from data.

        Args:
            data: Data to generate cache key from

        Returns:
            Cache key string (SHA256 hash)
        """
        # Serialize data to JSON and hash it
        try:
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except (TypeError, ValueError):
            # Fallback for non-serializable data
            return hashlib.sha256(str(data).encode()).hexdigest()

    async def get_cached(self, cache_key: str) -> Any | None:
        """
        Retrieve cached value.

        Args:
            cache_key: Cache key to retrieve

        Returns:
            Cached value or None if not found
        """
        if not self._cache_enabled:
            return None

        # Stub implementation - returns from in-memory dict
        return self._cache_data.get(cache_key)

    # stub-ok: Intentional stub - full caching backend (Redis/Memcached) in future phase
    async def set_cached(
        self, cache_key: str, value: Any, ttl_seconds: int = 3600
    ) -> None:
        """
        Store value in cache.

        Args:
            cache_key: Cache key to store under
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (not implemented in current version)
        """
        if self._cache_enabled:
            # Stub implementation - stores in in-memory dict
            # TTL is ignored in this stub version
            self._cache_data[cache_key] = value

    async def invalidate_cache(self, cache_key: str) -> None:
        """
        Invalidate a cache entry.

        Args:
            cache_key: Cache key to invalidate
        """
        self._cache_data.pop(cache_key, None)

    async def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache_data.clear()

    def get_cache_stats(self) -> TypedDictCacheStats:
        """
        Get cache statistics.

        Returns:
            Typed dictionary with cache statistics
        """
        return TypedDictCacheStats(
            enabled=self._cache_enabled,
            entries=len(self._cache_data),
            keys=list(self._cache_data.keys()),
        )
