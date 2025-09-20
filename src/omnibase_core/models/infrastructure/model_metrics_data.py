"""
Metrics data model.

Clean, strongly-typed replacement for custom metrics union types.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelMetric(BaseModel):
    """Universal metric model for any supported type."""

    key: str = Field(..., description="Metric key")
    value: Any = Field(..., description="Metric value (string, int, float, or bool)")
    metric_type: str = Field(
        ..., description="Type of metric (string, numeric, boolean)"
    )
    unit: str | None = Field(
        None, description="Unit of measurement (for numeric metrics)"
    )
    description: str | None = Field(None, description="Metric description")


class ModelMetricsData(BaseModel):
    """
    Clean, strongly-typed model replacing custom metrics union types.

    Eliminates: dict[str, str | int | bool | float]

    With proper structured data using a single generic metric type.
    """

    # Single list of universal metrics
    metrics: list[ModelMetric] = Field(
        default_factory=list, description="Collection of typed metrics"
    )

    # Metadata
    collection_name: str | None = Field(
        None, description="Name of the metrics collection"
    )

    category: str = Field(default="general", description="Category of metrics")

    tags: list[str] = Field(
        default_factory=list, description="Tags for organizing metrics"
    )

    def add_metric(
        self,
        key: str,
        value: str | int | float | bool,
        description: str | None = None,
        unit: str | None = None,
    ) -> None:
        """Add a metric with automatic type detection."""
        if isinstance(value, bool):  # Check bool first since bool is subclass of int
            metric_type = "boolean"
        elif isinstance(value, str):
            metric_type = "string"
        else:  # Must be int or float based on type annotation
            metric_type = "numeric"

        metric = ModelMetric(
            key=key,
            value=value,
            metric_type=metric_type,
            unit=unit,
            description=description,
        )
        self.metrics.append(metric)

    def get_metric_by_key(self, key: str) -> Any | None:
        """Get metric value by key."""
        for metric in self.metrics:
            if metric.key == key:
                return metric.value
        return None

    def get_all_keys(self) -> list[str]:
        """Get all metric keys."""
        return [metric.key for metric in self.metrics]

    def clear_all_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()

    def get_metrics_by_type(self, metric_type: str) -> list[ModelMetric]:
        """Get all metrics of a specific type."""
        return [metric for metric in self.metrics if metric.metric_type == metric_type]
