"""
HandlerCapabilityMetrics - Performance Metrics Collection Handler

Provides performance metrics collection capabilities for ONEX pipeline.
This is a pure handler replacement for MixinMetrics with no inheritance.

Usage:
    metrics = HandlerCapabilityMetrics(namespace="my_service")
    metrics.record_metric("latency_ms", 250.5, tags={"endpoint": "/api"})
    metrics.increment_counter("requests_total")
    current_metrics = metrics.get_metrics()

.. versionadded:: 0.4.0
    Added as part of Mixin-to-Handler conversion (OMN-1112)
"""

import copy

from pydantic import BaseModel, ConfigDict, PrivateAttr

from omnibase_core.types.typed_dict_mixin_types import TypedDictMetricEntry


class HandlerCapabilityMetrics(BaseModel):
    """
    Handler providing performance metrics collection capabilities.

    This is a standalone handler that replaces MixinMetrics.
    It uses composition instead of inheritance.

    Attributes:
        namespace: Metrics namespace for organization
        enabled: Whether metrics collection is enabled

    Thread Safety:
        Each instance maintains its own isolated metrics. Instances should not
        be shared across threads without external synchronization.

    .. versionadded:: 0.4.0
        Added as part of Mixin-to-Handler conversion (OMN-1112)
    """

    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    namespace: str = "onex"
    enabled: bool = True

    # Private attribute for internal state (not serialized)
    _metrics_data: dict[str, TypedDictMetricEntry] = PrivateAttr(default_factory=dict)

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
        if self.enabled:
            self._metrics_data[metric_name] = TypedDictMetricEntry(
                value=value,
                tags=tags or {},
            )

    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            counter_name: Name of the counter to increment
            value: Amount to increment by (default: 1)
        """
        if self.enabled:
            existing = self._metrics_data.get(counter_name)
            current: float = 0
            if existing is not None:
                current = existing["value"]
            self._metrics_data[counter_name] = TypedDictMetricEntry(
                value=current + value,
                tags={},
            )

    def get_metrics(self) -> dict[str, TypedDictMetricEntry]:
        """
        Get current metrics data.

        Returns:
            Dictionary of current metrics with typed metric entries.
            Returns a deep copy to prevent external mutation of internal state.

        Note:
            Deep copy is used (rather than shallow copy) because TypedDictMetricEntry
            contains nested 'tags' dict that could be mutated by callers. A shallow copy
            would allow `metrics["name"]["tags"]["key"] = "value"` to modify internal state.
            Deep copy ensures complete isolation at a small performance cost.
        """
        return copy.deepcopy(self._metrics_data)

    def reset_metrics(self) -> None:
        """Reset all metrics data."""
        self._metrics_data.clear()


__all__ = ["HandlerCapabilityMetrics"]
