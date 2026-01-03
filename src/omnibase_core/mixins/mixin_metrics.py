"""
MixinMetrics - Performance Metrics Collection Mixin

Provides performance metrics collection capabilities for ONEX nodes.
Supports optional external backends (Prometheus, OpenTelemetry, etc.)
while maintaining backward-compatible in-memory storage.

Usage:
    # Basic usage (in-memory only, backward compatible)
    class MyNode(NodeBase, MixinMetrics):
        def __init__(self, container):
            super().__init__(container)
            # Metrics tracking automatically available
            self.record_metric("startup_time_ms", 150.0)

    # With Prometheus backend
    from omnibase_core.backends.metrics import BackendMetricsPrometheus

    class MyNode(NodeBase, MixinMetrics):
        def __init__(self, container):
            super().__init__(container)
            self.set_metrics_backend(BackendMetricsPrometheus(prefix="myapp"))

.. versionchanged:: 0.5.7
    Added optional backend support for Prometheus and other external systems.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.types.typed_dict_mixin_types import TypedDictMetricEntry

if TYPE_CHECKING:
    from omnibase_core.protocols.metrics import ProtocolMetricsBackend


class MixinMetrics:
    """
    Mixin providing performance metrics collection.

    Supports both in-memory metrics storage and external backends
    (Prometheus, StatsD, OpenTelemetry, etc.) via the ProtocolMetricsBackend
    protocol.

    Attributes:
        _metrics_enabled: Whether metrics collection is enabled
        _metrics_data: In-memory metrics storage (always populated)
        _metrics_backend: Optional external metrics backend

    Note:
        The in-memory storage is always populated, regardless of whether
        an external backend is configured. This ensures existing code
        using get_metrics() continues to work.

    Thread Safety:
        WARNING: This mixin is NOT thread-safe by default. For thread-safe
        usage, use thread-local instances or external synchronization.
        If using an external backend, check its thread safety documentation.

    Example:
        .. code-block:: python

            from omnibase_core.mixins import MixinMetrics

            class MyService(MixinMetrics):
                def process_request(self):
                    # Record metrics
                    self.record_metric("request_duration_ms", 45.2)
                    self.increment_counter("requests_total")

                    # Get in-memory metrics
                    metrics = self.get_metrics()

            # With external backend
            from omnibase_core.backends.metrics import BackendMetricsPrometheus

            service = MyService()
            service.set_metrics_backend(
                BackendMetricsPrometheus(prefix="myservice")
            )
            service.record_metric("cpu_usage", 72.5)

    .. versionchanged:: 0.5.7
        Added optional backend support.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize metrics mixin."""
        super().__init__(*args, **kwargs)
        # Use object.__setattr__() to bypass Pydantic validation for internal state
        object.__setattr__(self, "_metrics_enabled", True)
        object.__setattr__(self, "_metrics_data", {})
        object.__setattr__(self, "_metrics_backend", None)

    def set_metrics_backend(self, backend: ProtocolMetricsBackend | None) -> None:
        """
        Set the external metrics backend.

        When a backend is set, metrics are forwarded to it in addition
        to being stored in-memory. This allows for external monitoring
        while maintaining legacy API support.

        Args:
            backend: Metrics backend implementing ProtocolMetricsBackend,
                or None to disable external backend

        Example:
            .. code-block:: python

                from omnibase_core.backends.metrics import BackendMetricsPrometheus

                node = MyNode()
                node.set_metrics_backend(BackendMetricsPrometheus())

                # Later, disable backend
                node.set_metrics_backend(None)

        .. versionadded:: 0.5.7
        """
        object.__setattr__(self, "_metrics_backend", backend)

    def get_metrics_backend(self) -> ProtocolMetricsBackend | None:
        """
        Get the current metrics backend.

        Returns:
            The configured metrics backend, or None if not set.

        .. versionadded:: 0.5.7
        """
        try:
            backend: ProtocolMetricsBackend | None = object.__getattribute__(
                self, "_metrics_backend"
            )
            return backend
        except AttributeError:
            return None

    def record_metric(
        self, metric_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a metric value (gauge).

        Records the metric to in-memory storage and optionally forwards
        to the configured external backend.

        Args:
            metric_name: Name of the metric to record
            value: Metric value
            tags: Optional tags for the metric

        Note:
            This method records a gauge-type metric (point-in-time value).
            For counters that only increase, use increment_counter().
        """
        # Defensive: Initialize if attributes don't exist
        try:
            metrics_enabled = object.__getattribute__(self, "_metrics_enabled")
        except AttributeError:
            object.__setattr__(self, "_metrics_enabled", True)
            metrics_enabled = True

        if metrics_enabled:
            # Always store in-memory for legacy API support
            try:
                metrics_data = object.__getattribute__(self, "_metrics_data")
            except AttributeError:
                object.__setattr__(self, "_metrics_data", {})
                metrics_data = object.__getattribute__(self, "_metrics_data")

            metrics_data[metric_name] = {
                "value": value,
                "tags": tags or {},
            }

            # Forward to backend if configured
            try:
                backend: ProtocolMetricsBackend | None = object.__getattribute__(
                    self, "_metrics_backend"
                )
            except AttributeError:
                backend = None

            if backend is not None:
                backend.record_gauge(metric_name, value, tags)

    def increment_counter(
        self, counter_name: str, value: int = 1, tags: dict[str, str] | None = None
    ) -> None:
        """
        Increment a counter metric.

        Records the counter to in-memory storage and optionally forwards
        to the configured external backend.

        Args:
            counter_name: Name of the counter to increment
            value: Amount to increment by (default: 1)
            tags: Optional tags for the counter

        .. versionchanged:: 0.5.7
            Added optional tags parameter.
        """
        # Defensive: Initialize if attributes don't exist
        try:
            metrics_enabled = object.__getattribute__(self, "_metrics_enabled")
        except AttributeError:
            object.__setattr__(self, "_metrics_enabled", True)
            metrics_enabled = True

        if metrics_enabled:
            try:
                metrics_data = object.__getattribute__(self, "_metrics_data")
            except AttributeError:
                object.__setattr__(self, "_metrics_data", {})
                metrics_data = object.__getattribute__(self, "_metrics_data")

            current = metrics_data.get(counter_name, {"value": 0})["value"]
            metrics_data[counter_name] = {"value": current + value}

            # Forward to backend if configured
            try:
                backend: ProtocolMetricsBackend | None = object.__getattribute__(
                    self, "_metrics_backend"
                )
            except AttributeError:
                backend = None

            if backend is not None:
                backend.increment_counter(counter_name, float(value), tags)

    def record_histogram(
        self, histogram_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a histogram observation.

        Records the observation to in-memory storage (as a gauge) and
        forwards to the configured external backend (as a histogram).

        Args:
            histogram_name: Name of the histogram
            value: Observed value
            tags: Optional tags for the histogram

        Note:
            In-memory storage only keeps the last value (like a gauge).
            For proper histogram distribution tracking, use an external
            backend like Prometheus.

        .. versionadded:: 0.5.7
        """
        # Defensive: Initialize if attributes don't exist
        try:
            metrics_enabled = object.__getattribute__(self, "_metrics_enabled")
        except AttributeError:
            object.__setattr__(self, "_metrics_enabled", True)
            metrics_enabled = True

        if metrics_enabled:
            # Store in-memory as gauge (last value only)
            try:
                metrics_data = object.__getattribute__(self, "_metrics_data")
            except AttributeError:
                object.__setattr__(self, "_metrics_data", {})
                metrics_data = object.__getattribute__(self, "_metrics_data")

            metrics_data[histogram_name] = {
                "value": value,
                "tags": tags or {},
            }

            # Forward to backend as proper histogram if configured
            try:
                backend: ProtocolMetricsBackend | None = object.__getattribute__(
                    self, "_metrics_backend"
                )
            except AttributeError:
                backend = None

            if backend is not None:
                backend.record_histogram(histogram_name, value, tags)

    def push_metrics(self) -> None:
        """
        Push metrics to the external backend.

        For push-based backends (like Prometheus Pushgateway), this method
        sends accumulated metrics to the remote server. For pull-based
        backends or when no backend is configured, this is a no-op.

        .. versionadded:: 0.5.7
        """
        try:
            backend: ProtocolMetricsBackend | None = object.__getattribute__(
                self, "_metrics_backend"
            )
        except AttributeError:
            backend = None

        if backend is not None:
            backend.push()

    def get_metrics(self) -> dict[str, TypedDictMetricEntry]:
        """
        Get current metrics data from in-memory storage.

        Returns:
            Dictionary of current metrics with typed metric entries

        Note:
            This returns a copy of the in-memory metrics storage.
            If using an external backend, query the backend directly
            for its metrics data.
        """
        # Defensive: Initialize _metrics_data if it doesn't exist
        try:
            metrics_data: dict[str, TypedDictMetricEntry] = object.__getattribute__(
                self, "_metrics_data"
            )
        except AttributeError:
            object.__setattr__(self, "_metrics_data", {})
            metrics_data = object.__getattribute__(self, "_metrics_data")
        result: dict[str, TypedDictMetricEntry] = metrics_data.copy()
        return result

    def reset_metrics(self) -> None:
        """
        Reset all in-memory metrics data.

        Note:
            This only clears the in-memory storage. External backends
            maintain their own state and are not affected by this method.
        """
        # Defensive: Initialize if attributes don't exist
        try:
            metrics_data = object.__getattribute__(self, "_metrics_data")
        except AttributeError:
            object.__setattr__(self, "_metrics_data", {})
            metrics_data = object.__getattribute__(self, "_metrics_data")
        metrics_data.clear()
