"""
Cache backend implementations for optional L2 caching.

This module provides implementations of ProtocolCacheBackend for various
distributed caching systems.

Available Backends:
    - BackendCacheRedis: Redis/Valkey backend with async support

Utility Functions:
    - sanitize_redis_url: Remove credentials from Redis URLs for safe logging
    - sanitize_error_message: Sanitize error messages to prevent credential leakage

Constants:
    - REDIS_AVAILABLE: Boolean indicating if redis package is installed

Usage:
    .. code-block:: python

        from omnibase_core.backends.cache import (
            BackendCacheRedis,
            REDIS_AVAILABLE,
            sanitize_redis_url,
        )
        from omnibase_core.mixins import MixinCaching
        from omnibase_core.nodes import NodeCompute

        # Check if Redis is available
        if REDIS_AVAILABLE:
            # Create Redis backend
            backend = BackendCacheRedis(url="redis://localhost:6379/0")
            await backend.connect()

            # Use with MixinCaching
            class MyNode(NodeCompute, MixinCaching):
                def __init__(self, container):
                    super().__init__(container, backend=backend)

        # Sanitize URLs for safe logging
        safe_url = sanitize_redis_url("redis://user:pass@host:6379")
        # Returns: "redis://***:***@host:6379"

Requirements:
    The redis package is an optional dependency. Install with:
    poetry install -E cache

.. versionadded:: 0.5.0
"""

from omnibase_core.backends.cache.backend_cache_redis import (
    REDIS_AVAILABLE,
    BackendCacheRedis,
    sanitize_error_message,
    sanitize_redis_url,
)

__all__ = [
    "BackendCacheRedis",
    "REDIS_AVAILABLE",
    "sanitize_error_message",
    "sanitize_redis_url",
]
