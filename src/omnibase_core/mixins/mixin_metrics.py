"""
MixinMetrics - Performance Metrics Collection Mixin

Provides performance metrics collection capabilities for ONEX nodes.
This is a stub implementation - full metrics collection to be implemented in future phases.

Usage:
    class MyNode(NodeBase, MixinMetrics):
        def __init__(self, container):
            super().__init__(container)
            # Metrics tracking automatically available
"""

from typing import Any

from omnibase_core.types.typed_dict_mixin_types import TypedDictMetricEntry


class MixinMetrics:
    """
    Mixin providing performance metrics collection.

    This is a stub implementation providing the interface for metrics collection.
    Full implementation with metrics backends (Prometheus, StatsD, etc.) will be
    added in future phases.

    Attributes:
        _metrics_enabled: Whether metrics collection is enabled
        _metrics_data: In-memory metrics storage (stub)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize metrics mixin."""
        super().__init__(*args, **kwargs)
        # Use object.__setattr__() to bypass Pydantic validation for internal state
        object.__setattr__(self, "_metrics_enabled", True)
        object.__setattr__(self, "_metrics_data", {})

    def record_metric(
        self, metric_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of the metric to record
            value: Metric value
            tags: Optional tags for the metric
        """
        # Stub implementation - metrics will be sent to backend in future
        # Use object.__getattribute__() to access attributes set with object.__setattr__()
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

            metrics_data[metric_name] = {
                "value": value,
                "tags": tags or {},
            }

    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            counter_name: Name of the counter to increment
            value: Amount to increment by (default: 1)
        """
        # Use object.__getattribute__() to access attributes set with object.__setattr__()
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

    def get_metrics(self) -> dict[str, TypedDictMetricEntry]:
        """
        Get current metrics data.

        Returns:
            Dictionary of current metrics with typed metric entries
        """
        # Use object.__getattribute__() to access attributes set with object.__setattr__()
        # Defensive: Initialize _metrics_data if it doesn't exist (e.g., if __init__ wasn't called)
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
        """Reset all metrics data."""
        # Use object.__getattribute__() to access attributes set with object.__setattr__()
        # Defensive: Initialize if attributes don't exist
        try:
            metrics_data = object.__getattribute__(self, "_metrics_data")
        except AttributeError:
            object.__setattr__(self, "_metrics_data", {})
            metrics_data = object.__getattribute__(self, "_metrics_data")
        metrics_data.clear()
