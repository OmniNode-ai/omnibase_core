"""
HandlerCapabilityCaching - Result Caching Handler.

Provides result caching capabilities for ONEX pipeline.
This is a pure handler replacement for MixinCaching with no inheritance.

This is a standalone handler that uses composition instead of mixin inheritance.
It can be embedded in any component that needs caching capabilities.

Usage:
    >>> cache = HandlerCapabilityCaching(default_ttl_seconds=600)
    >>> cache_key = cache.generate_cache_key({"param": "value"})
    >>> await cache.set_cached(cache_key, result)
    >>> cached = await cache.get_cached(cache_key)

Ticket: OMN-1112

.. versionadded:: 0.4.0
    Added as part of Mixin-to-Handler conversion (OMN-1112)
"""

import hashlib
import json
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.types.typed_dict_mixin_types import TypedDictCacheStats


class HandlerCapabilityCaching(BaseModel):
    """
    Handler providing result caching capabilities.

    This is a standalone Pydantic model handler that replaces MixinCaching.
    It uses composition instead of inheritance, allowing it to be embedded
    in any component that needs caching capabilities.

    Attributes:
        enabled: Whether caching is enabled (default True)
        default_ttl_seconds: Default time-to-live for cached entries (default 3600)

    Example:
        >>> cache = HandlerCapabilityCaching(enabled=True, default_ttl_seconds=600)
        >>> key = cache.generate_cache_key({"user_id": 123})
        >>> await cache.set_cached(key, {"result": "data"})
        >>> result = await cache.get_cached(key)

    Thread Safety:
        Each instance maintains its own isolated cache. Instances should not
        be shared across threads without external synchronization.

    .. versionadded:: 0.4.0
        Added as part of Mixin-to-Handler conversion (OMN-1112)
    """

    # TODO(OMN-TBD): Implement production-ready cache backend  [NEEDS TICKET]
    # Current stub implementation stores in-memory dict without TTL enforcement.
    # Production implementation should use Redis/Memcached with proper TTL,
    # LRU eviction, and distributed cache support.

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    enabled: bool = True
    default_ttl_seconds: int = Field(
        default=3600,
        ge=0,
        le=31536000,
        description="Default TTL in seconds (max 1 year)",
    )

    # Class-level constant for stub implementation
    MAX_STUB_ENTRIES: ClassVar[int] = 10000

    # Private attribute for internal cache storage (not serialized)
    _cache_data: dict[str, object] = PrivateAttr(default_factory=dict)

    def generate_cache_key(self, data: Any) -> str:
        """
        Generate a cache key from data using SHA256 hash.

        Args:
            data: Data to generate cache key from. Can be any JSON-serializable
                  value, or any object with a string representation.

        Returns:
            64-character hexadecimal SHA256 hash string.

        Note:
            Uses sort_keys=True for deterministic key generation from dicts.
            Falls back to str() representation for non-JSON-serializable objects.
        """
        try:
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except VALIDATION_ERRORS:
            # fallback-ok: use string representation for non-serializable data
            return hashlib.sha256(str(data).encode()).hexdigest()

    async def get_cached(self, cache_key: str) -> Any | None:
        """
        Retrieve cached value.

        Args:
            cache_key: Cache key to retrieve.

        Returns:
            Cached value if found and caching is enabled, None otherwise.
        """
        if not self.enabled:
            return None
        return self._cache_data.get(cache_key)

    async def set_cached(  # stub-ok: TTL enforcement deferred to production backend
        self, cache_key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """
        Store value in cache.

        Args:
            cache_key: Cache key to store under.
            value: Value to cache.
            ttl_seconds: Time-to-live in seconds. Not enforced in current
                         stub implementation but accepted for API compatibility.

        Note:
            This is a stub implementation. TTL enforcement will be added
            when a persistent cache backend (Redis/Memcached) is integrated.
        """
        if self.enabled:
            # stub-impl-ok: Basic max_entries enforcement for memory safety
            # Production implementation will use proper LRU eviction
            if len(self._cache_data) >= self.MAX_STUB_ENTRIES:
                # Simple eviction: remove oldest entry (first key)
                oldest_key = next(iter(self._cache_data))
                del self._cache_data[oldest_key]
            # stub-ok: TTL parameter accepted but not enforced in stub implementation
            self._cache_data[cache_key] = value

    async def invalidate_cache(self, cache_key: str) -> None:
        """
        Invalidate a cache entry.

        Args:
            cache_key: Cache key to invalidate. If key does not exist,
                       this operation is a no-op.
        """
        self._cache_data.pop(cache_key, None)

    async def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache_data.clear()

    def get_cache_stats(self) -> TypedDictCacheStats:
        """
        Get cache statistics.

        Returns:
            TypedDictCacheStats containing:
                - enabled: Whether caching is enabled
                - entries: Number of entries in cache
                - keys: List of all cache keys
        """
        return TypedDictCacheStats(
            enabled=self.enabled,
            entries=len(self._cache_data),
            keys=list(self._cache_data.keys()),
        )


__all__ = ["HandlerCapabilityCaching"]
