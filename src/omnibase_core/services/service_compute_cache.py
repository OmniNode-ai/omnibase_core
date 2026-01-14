"""
ServiceComputeCache - Default ProtocolComputeCache implementation.

Wraps ModelComputeCache to satisfy the ProtocolComputeCache protocol.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import Any

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)
from omnibase_core.models.infrastructure import ModelComputeCache
from omnibase_core.protocols.compute import ProtocolComputeCache

__all__ = ["ServiceComputeCache"]


class ServiceComputeCache:
    """
    Default ProtocolComputeCache implementation using ModelComputeCache.

    This adapter wraps ModelComputeCache to satisfy ProtocolComputeCache,
    providing a default implementation when no cache is injected.

    Thread Safety:
        NOT thread-safe. This class wraps ModelComputeCache which uses
        a standard Python dict internally. Concurrent access from multiple
        threads may cause:

        - Data corruption from non-atomic read-modify-write operations
        - Race conditions during cache eviction
        - Inconsistent cache statistics

        For thread-safe usage:

        - Use separate ServiceComputeCache instances per thread, OR
        - Wrap all cache operations with threading.Lock::

            import threading
            lock = threading.Lock()
            with lock:
                cache.put("key", value)
            with lock:
                result = cache.get("key")

        See docs/guides/THREADING.md for detailed guidelines.

    Example:
        >>> config = ModelComputeCacheConfig(max_size=256)
        >>> cache = ServiceComputeCache(config)
        >>> cache.put("key", "value")
        >>> cache.get("key")
        'value'

    .. versionadded:: 0.4.0
    """

    def __init__(self, config: ModelComputeCacheConfig) -> None:
        """
        Initialize cache service from configuration.

        Args:
            config: Cache configuration (size, TTL, eviction policy)
        """
        self._cache = ModelComputeCache(
            max_size=config.max_size,
            ttl_seconds=config.ttl_seconds,
            eviction_policy=config.eviction_policy,
            enable_stats=config.enable_stats,
        )
        self._config = config

    @property
    def max_size(self) -> int:
        """Maximum cache size."""
        return self._cache.max_size

    @property
    def eviction_policy(self) -> Any:
        """Cache eviction policy."""
        return self._cache.eviction_policy

    @property
    def ttl(self) -> Any:
        """Cache TTL as timedelta."""
        return self._cache.ttl

    @property
    def default_ttl_minutes(self) -> int:
        """Default TTL in minutes."""
        return self._cache.default_ttl_minutes

    @property
    def enable_stats(self) -> bool:
        """Whether stats are enabled."""
        return self._cache.enable_stats

    @standard_error_handling("Cache get")
    def get(self, cache_key: str) -> Any | None:
        """Get cached value if valid and not expired."""
        return self._cache.get(cache_key)

    @standard_error_handling("Cache put")
    def put(self, cache_key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """Cache value with optional TTL."""
        self._cache.put(cache_key, value, ttl_minutes)

    @standard_error_handling("Cache clear")
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    @standard_error_handling("Cache stats")
    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics."""
        return self._cache.get_stats()


# Verify protocol compliance
_cache_check: ProtocolComputeCache = ServiceComputeCache(ModelComputeCacheConfig())
