"""
Cache backends for L2 distributed caching.

This module provides implementations of ProtocolCacheBackend for various
distributed caching systems.

Available Backends:
    - BackendCacheRedis: Redis/Valkey backend with async support

Usage:
    from omnibase_core.infrastructure.cache_backends import BackendCacheRedis

    # Create Redis backend
    backend = BackendCacheRedis(url="redis://localhost:6379/0")
    await backend.connect()

    # Use with MixinCaching
    class MyNode(NodeCompute, MixinCaching):
        def __init__(self, container):
            super().__init__(container, backend=backend)

Requirements:
    The redis package is an optional dependency. Install with:
    poetry install -E cache

.. versionadded:: 0.5.0
"""

from omnibase_core.infrastructure.cache_backends.backend_cache_redis import (
    BackendCacheRedis,
    REDIS_AVAILABLE,
)

__all__ = ["BackendCacheRedis", "REDIS_AVAILABLE"]
