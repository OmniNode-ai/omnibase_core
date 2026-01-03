"""
Backends Module - Pluggable backend implementations.

This module provides backend implementations for various infrastructure
concerns like metrics, logging, caching, and tracing. Backends implement
protocols defined in omnibase_core.protocols.

Module Organization:
    - cache/: Cache backend implementations (Redis, etc.)
    - metrics/: Metrics backend implementations (Prometheus, In-Memory, etc.)

Usage:
    .. code-block:: python

        from omnibase_core.backends.cache import BackendCacheRedis
        from omnibase_core.backends.metrics import (
            BackendMetricsInMemory,
            BackendMetricsPrometheus,
        )

.. versionadded:: 0.5.7
"""

from omnibase_core.backends.cache import (
    REDIS_AVAILABLE,
    BackendCacheRedis,
)
from omnibase_core.backends.metrics import (
    BackendMetricsInMemory,
)

__all__ = [
    # Cache backends
    "BackendCacheRedis",
    "REDIS_AVAILABLE",
    # Metrics backends
    "BackendMetricsInMemory",
]

# Conditionally export Prometheus backend if prometheus-client is installed
try:
    from omnibase_core.backends.metrics import (  # noqa: F401
        BackendMetricsPrometheus,
    )

    __all__.append("BackendMetricsPrometheus")
except ImportError:
    # prometheus-client not installed, Prometheus backend not available
    pass
