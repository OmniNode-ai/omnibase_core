"""
BackendMetricsInMemory - In-memory metrics backend for testing and development.

This backend stores metrics in memory without sending them to any external
system. It's useful for testing, development, and as a fallback when no
external metrics system is configured.

Thread Safety:
    WARNING: This backend is NOT thread-safe. For thread-safe usage,
    wrap access with appropriate synchronization or use one instance per thread.

Usage:
    .. code-block:: python

        from omnibase_core.backends.metrics import BackendMetricsInMemory

        backend = BackendMetricsInMemory()

        # Record metrics
        backend.record_gauge("temperature", 23.5, tags={"location": "room1"})
        backend.increment_counter("requests_total")
        backend.record_histogram("response_time", 0.123)

        # Retrieve metrics for assertions or inspection
        gauges = backend.get_gauges()
        counters = backend.get_counters()
        histograms = backend.get_histograms()

        # Clear all metrics
        backend.clear()

.. versionadded:: 0.5.7
"""

from __future__ import annotations

__all__ = [
    "BackendMetricsInMemory",
]


class BackendMetricsInMemory:
    """
    In-memory metrics backend for testing and development.

    Stores all metrics in-memory dictionaries, providing methods to
    retrieve and inspect collected metrics for testing purposes.

    Attributes:
        _gauges: Dictionary of gauge metric values by key
        _counters: Dictionary of counter metric values by key
        _histograms: Dictionary of histogram observations by key

    Thread Safety:
        NOT thread-safe. Use synchronization for multi-threaded access.

    Example:
        .. code-block:: python

            backend = BackendMetricsInMemory()
            backend.record_gauge("cpu_usage", 45.2, tags={"host": "server1"})

            # Check the recorded value
            gauges = backend.get_gauges()
            assert "cpu_usage{host=server1}" in gauges
            assert gauges["cpu_usage{host=server1}"] == 45.2

    .. versionadded:: 0.5.7
    """

    def __init__(self) -> None:
        """Initialize the in-memory metrics backend."""
        self._gauges: dict[str, float] = {}
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a gauge metric value.

        Args:
            name: Name of the gauge metric
            value: Current value
            tags: Optional labels/tags for the metric
        """
        key = self._make_key(name, tags)
        self._gauges[key] = value

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Name of the counter metric
            value: Amount to increment by (default: 1.0)
            tags: Optional labels/tags for the metric
        """
        key = self._make_key(name, tags)
        self._counters[key] = self._counters.get(key, 0.0) + value

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a histogram observation.

        Args:
            name: Name of the histogram metric
            value: Observed value
            tags: Optional labels/tags for the metric
        """
        key = self._make_key(name, tags)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def push(self) -> None:
        """
        Push metrics to remote backend.

        For in-memory backend, this is a no-op since there is no
        remote backend to push to.
        """
        # No-op for in-memory backend

    def get_gauges(self) -> dict[str, float]:
        """
        Get all gauge metric values.

        Returns:
            Dictionary mapping metric keys to their current values.
        """
        return self._gauges.copy()

    def get_counters(self) -> dict[str, float]:
        """
        Get all counter metric values.

        Returns:
            Dictionary mapping counter keys to their current values.
        """
        return self._counters.copy()

    def get_histograms(self) -> dict[str, list[float]]:
        """
        Get all histogram observations.

        Returns:
            Dictionary mapping histogram keys to lists of observations.
        """
        return {k: list(v) for k, v in self._histograms.items()}

    def clear(self) -> None:
        """Clear all collected metrics."""
        self._gauges.clear()
        self._counters.clear()
        self._histograms.clear()

    def _make_key(self, name: str, tags: dict[str, str] | None) -> str:
        """
        Create a unique key for a metric with tags.

        Args:
            name: Metric name
            tags: Optional metric tags

        Returns:
            Unique key string incorporating name and tags.
        """
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}{{{tag_str}}}"
        return name
