"""
Metrics data model.

Clean, strongly-typed replacement for custom metrics union types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

# Union import removed - using strongly-typed discriminated unions
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_metric_data_type import EnumMetricDataType
from ...enums.enum_metrics_category import EnumMetricsCategory
from .model_metric import ModelMetric


class ModelMetricsData(BaseModel):
    """
    Clean, strongly-typed model replacing custom metrics union types.

    Eliminates: dict[str, str | int | bool | float]

    With proper structured data using a single generic metric type.
    """

    # Single list of universal metrics using discriminated union pattern
    metrics: list[ModelMetric] = Field(
        default_factory=list, description="Collection of typed metrics"
    )

    # Metadata
    collection_id: UUID | None = Field(None, description="UUID for metrics collection")
    collection_display_name: str | None = Field(
        None, description="Human-readable name of the metrics collection"
    )

    category: EnumMetricsCategory = Field(
        default=EnumMetricsCategory.GENERAL, description="Category of metrics"
    )

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
        """Add a metric with automatic type detection using factory methods."""
        metric = ModelMetric.from_any_value(
            key=key, value=value, unit=unit, description=description
        )
        self.metrics.append(metric)

    def get_metric_by_key(self, key: str) -> str | int | float | bool | None:
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

    def get_metrics_by_type(self, metric_type: EnumMetricDataType) -> list[ModelMetric]:
        """Get all metrics of a specific type."""
        return [metric for metric in self.metrics if metric.metric_type == metric_type]

    @property
    def collection_name(self) -> str | None:
        """Access collection name."""
        return self.collection_display_name

    @collection_name.setter
    def collection_name(self, value: str | None) -> None:
        """Set collection name and generate corresponding ID."""
        if value:
            import hashlib

            collection_hash = hashlib.sha256(value.encode()).hexdigest()
            self.collection_id = UUID(
                f"{collection_hash[:8]}-{collection_hash[8:12]}-{collection_hash[12:16]}-{collection_hash[16:20]}-{collection_hash[20:32]}"
            )
        else:
            self.collection_id = None
        self.collection_display_name = value


# Export for use
__all__ = ["ModelMetricsData"]
