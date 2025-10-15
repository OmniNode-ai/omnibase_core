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

from typing import Any, Dict


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
        self._metrics_enabled = True
        self._metrics_data: Dict[str, Any] = {}

    def record_metric(
        self, metric_name: str, value: float, tags: Dict[str, str] | None = None
    ) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of the metric to record
            value: Metric value
            tags: Optional tags for the metric
        """
        # Stub implementation - metrics will be sent to backend in future
        if self._metrics_enabled:
            self._metrics_data[metric_name] = {
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
        if self._metrics_enabled:
            current = self._metrics_data.get(counter_name, {"value": 0})["value"]
            self._metrics_data[counter_name] = {"value": current + value}

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics data.

        Returns:
            Dictionary of current metrics
        """
        return self._metrics_data.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics data."""
        self._metrics_data.clear()
