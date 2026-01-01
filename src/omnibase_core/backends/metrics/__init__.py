"""
Metrics Backends Module - Backend implementations for metrics collection.

This module provides backend implementations for metrics collection,
supporting different metrics systems like Prometheus, StatsD, etc.

Available Backends:
    - BackendMetricsInMemory: In-memory backend for testing and development
    - BackendMetricsPrometheus: Prometheus backend (requires prometheus-client)

Usage:
    .. code-block:: python

        from omnibase_core.backends.metrics import BackendMetricsInMemory

        # Create an in-memory backend for testing
        backend = BackendMetricsInMemory()
        backend.record_gauge("memory_usage", 1024.0)
        backend.increment_counter("requests_total")

        # Get collected metrics
        print(backend.get_gauges())
        print(backend.get_counters())

Prometheus Usage (when prometheus-client is installed):

    .. code-block:: python

        from omnibase_core.backends.metrics import BackendMetricsPrometheus

        # Create a Prometheus backend
        backend = BackendMetricsPrometheus(
            prefix="myapp",
            push_gateway_url="http://localhost:9091",  # Optional
        )
        backend.record_gauge("memory_usage", 1024.0)
        backend.push()  # Push to gateway if configured

.. versionadded:: 0.5.7
"""

from omnibase_core.backends.metrics.backend_metrics_in_memory import (
    BackendMetricsInMemory,
)

__all__ = [
    "BackendMetricsInMemory",
]

# Conditionally export Prometheus backend if available
try:
    from omnibase_core.backends.metrics.backend_metrics_prometheus import (  # noqa: F401
        BackendMetricsPrometheus,
    )

    __all__.append("BackendMetricsPrometheus")
except ImportError:
    # prometheus-client not installed, Prometheus backend not available
    pass
