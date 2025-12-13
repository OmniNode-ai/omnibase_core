"""
ServiceComputeCache - Default ProtocolComputeCache implementation.

Wraps ModelComputeCache to satisfy the ProtocolComputeCache protocol.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import Any

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
        NOT thread-safe. See ModelComputeCache for details.

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

    def get(self, cache_key: str) -> Any | None:
        """Get cached value if valid and not expired."""
        return self._cache.get(cache_key)

    def put(self, cache_key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """Cache value with optional TTL."""
        self._cache.put(cache_key, value, ttl_minutes)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics."""
        return self._cache.get_stats()


# Verify protocol compliance
_cache_check: ProtocolComputeCache = ServiceComputeCache(ModelComputeCacheConfig())
