"""
Cache backends for L2 distributed caching.

.. deprecated:: 0.5.1
    This module is deprecated. Import from ``omnibase_core.backends.cache`` instead.

This module re-exports from ``omnibase_core.backends.cache`` for legacy
support. The canonical location is now ``omnibase_core.backends.cache``.

Available Backends:
    - BackendCacheRedis: Redis/Valkey backend with async support

Usage:
    # Preferred (new location):
    from omnibase_core.backends.cache import BackendCacheRedis

    # Deprecated (this module - still works):
    from omnibase_core.infrastructure.cache_backends import BackendCacheRedis

Requirements:
    The redis package is an optional dependency. Install with:
    poetry install -E cache

.. versionadded:: 0.5.0
.. versionchanged:: 0.5.1
    Moved to ``omnibase_core.backends.cache``. This module now re-exports.
"""

# Re-export from canonical location (deprecated module)
from omnibase_core.backends.cache import (
    REDIS_AVAILABLE,
    BackendCacheRedis,
)

__all__ = ["BackendCacheRedis", "REDIS_AVAILABLE"]
