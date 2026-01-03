"""
Metrics Protocol Module - Backend abstractions for metrics collection.

This module provides protocol definitions for metrics backends,
enabling pluggable metrics implementations (Prometheus, StatsD, OpenTelemetry, etc.)
while maintaining a consistent interface.

Usage:
    from omnibase_core.protocols.metrics import ProtocolMetricsBackend

    class MyBackend:
        '''Custom metrics backend implementation.'''

        def record_gauge(
            self, name: str, value: float, tags: dict[str, str] | None = None
        ) -> None:
            # Custom implementation
            pass

        def increment_counter(
            self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
        ) -> None:
            # Custom implementation
            pass

        def record_histogram(
            self, name: str, value: float, tags: dict[str, str] | None = None
        ) -> None:
            # Custom implementation
            pass

        def push(self) -> None:
            # Push metrics to remote (optional)
            pass

.. versionadded:: 0.5.7
"""

from omnibase_core.protocols.metrics.protocol_metrics_backend import (
    ProtocolMetricsBackend,
)

__all__ = [
    "ProtocolMetricsBackend",
]
