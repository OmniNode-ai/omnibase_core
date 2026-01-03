"""
ProtocolMetricsBackend - Protocol for metrics backend implementations.

This protocol defines the interface for metrics backends used by MixinMetrics,
enabling pluggable implementations for different metrics systems like
Prometheus, StatsD, OpenTelemetry, etc.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations satisfy the contract. This enables consistent metrics
    collection across the ONEX ecosystem while allowing backend flexibility.

Thread Safety:
    WARNING: Thread safety is implementation-specific. Callers should verify
    the thread safety guarantees of their chosen implementation.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.metrics import ProtocolMetricsBackend

        def track_operation(
            backend: ProtocolMetricsBackend,
            operation_name: str,
            duration_ms: float,
        ) -> None:
            '''Track an operation using the metrics backend.'''
            backend.record_gauge(
                name=f"operation_{operation_name}_duration_ms",
                value=duration_ms,
                tags={"operation": operation_name},
            )
            backend.increment_counter(
                name=f"operation_{operation_name}_count",
                tags={"operation": operation_name},
            )

Related:
    - MixinMetrics: Primary consumer of ProtocolMetricsBackend implementations
    - BackendMetricsPrometheus: Prometheus implementation
    - BackendMetricsInMemory: In-memory implementation for testing

.. versionadded:: 0.5.7
"""

from __future__ import annotations

__all__ = [
    "ProtocolMetricsBackend",
]

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolMetricsBackend(Protocol):
    """
    Protocol for metrics backend implementations.

    Defines the interface for metrics backends used by MixinMetrics
    to send metrics to external systems (Prometheus, StatsD, etc.).

    Required Methods:
        - record_gauge: Record a gauge metric (point-in-time value)
        - increment_counter: Increment a counter metric
        - record_histogram: Record a histogram/distribution metric
        - push: Push metrics to remote backend (optional, may be no-op)

    Thread Safety:
        WARNING: Implementations are NOT guaranteed to be thread-safe.
        See implementation-specific documentation for thread safety guarantees.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.metrics import ProtocolMetricsBackend

            class SimpleMetricsBackend:
                '''Minimal metrics backend implementation.'''

                def __init__(self) -> None:
                    self._gauges: dict[str, float] = {}
                    self._counters: dict[str, float] = {}
                    self._histograms: dict[str, list[float]] = {}

                def record_gauge(
                    self,
                    name: str,
                    value: float,
                    tags: dict[str, str] | None = None,
                ) -> None:
                    key = self._make_key(name, tags)
                    self._gauges[key] = value

                def increment_counter(
                    self,
                    name: str,
                    value: float = 1.0,
                    tags: dict[str, str] | None = None,
                ) -> None:
                    key = self._make_key(name, tags)
                    self._counters[key] = self._counters.get(key, 0.0) + value

                def record_histogram(
                    self,
                    name: str,
                    value: float,
                    tags: dict[str, str] | None = None,
                ) -> None:
                    key = self._make_key(name, tags)
                    if key not in self._histograms:
                        self._histograms[key] = []
                    self._histograms[key].append(value)

                def push(self) -> None:
                    pass  # No-op for in-memory backend

                def _make_key(
                    self, name: str, tags: dict[str, str] | None
                ) -> str:
                    if tags:
                        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
                        return f"{name}{{{tag_str}}}"
                    return name

            # Verify protocol conformance
            backend: ProtocolMetricsBackend = SimpleMetricsBackend()
            assert isinstance(backend, ProtocolMetricsBackend)

    .. versionadded:: 0.5.7
    """

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a gauge metric (point-in-time value).

        Gauges represent a value that can go up or down, such as
        current memory usage, active connections, or temperature.

        Args:
            name: Name of the metric (e.g., "memory_usage_bytes")
            value: Current value of the metric
            tags: Optional labels/tags for the metric

        Note:
            Tags are used to add dimensions to metrics. Different tag
            combinations create separate metric series.
        """
        ...

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter metric.

        Counters represent a cumulative value that only increases,
        such as request counts, bytes sent, or errors encountered.

        Args:
            name: Name of the counter (e.g., "requests_total")
            value: Amount to increment by (default: 1.0)
            tags: Optional labels/tags for the metric

        Note:
            Counter values should generally be positive. The Prometheus
            convention is to use _total suffix for counter names.
        """
        ...

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a histogram/distribution metric.

        Histograms track the distribution of values, such as
        request latencies or response sizes. They provide quantiles,
        counts, and sums.

        Args:
            name: Name of the histogram (e.g., "request_duration_seconds")
            value: Observed value to record
            tags: Optional labels/tags for the metric

        Note:
            Histogram bucket boundaries are typically configured at
            initialization time based on expected value ranges.
        """
        ...

    def push(self) -> None:
        """
        Push metrics to remote backend.

        For push-based backends (like Prometheus Pushgateway),
        this method sends accumulated metrics to the remote server.

        For pull-based backends (like standard Prometheus),
        this method may be a no-op or trigger a metrics snapshot.

        Note:
            This method is optional for pull-based systems.
            Implementations should document their push behavior.
        """
        ...
