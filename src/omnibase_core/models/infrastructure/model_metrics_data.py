"""
Metrics data model.

Clean, strongly-typed replacement for custom metrics union types.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelStringMetric(BaseModel):
    """Model for string-based metrics."""

    key: str = Field(..., description="Metric key")
    value: str = Field(..., description="String metric value")
    description: str | None = Field(None, description="Metric description")


class ModelNumericMetric(BaseModel):
    """Model for numeric metrics."""

    key: str = Field(..., description="Metric key")
    value: int | float = Field(..., description="Numeric metric value")
    unit: str | None = Field(None, description="Unit of measurement")
    description: str | None = Field(None, description="Metric description")


class ModelBooleanMetric(BaseModel):
    """Model for boolean metrics."""

    key: str = Field(..., description="Metric key")
    value: bool = Field(..., description="Boolean metric value")
    description: str | None = Field(None, description="Metric description")


class ModelMetricsData(BaseModel):
    """
    Clean, strongly-typed model replacing custom metrics union types.

    Eliminates: dict[str, str | int | bool | float]

    With proper structured data using specific field types.
    """

    # Organized metrics by type
    string_metrics: list[ModelStringMetric] = Field(
        default_factory=list, description="String-based metrics"
    )

    numeric_metrics: list[ModelNumericMetric] = Field(
        default_factory=list, description="Numeric metrics"
    )

    boolean_metrics: list[ModelBooleanMetric] = Field(
        default_factory=list, description="Boolean metrics"
    )

    # Metadata
    collection_name: str | None = Field(
        None, description="Name of the metrics collection"
    )

    category: str = Field(default="general", description="Category of metrics")

    tags: list[str] = Field(
        default_factory=list, description="Tags for organizing metrics"
    )

    def add_string_metric(
        self, key: str, value: str, description: str | None = None
    ) -> None:
        """Add a string metric."""
        self.string_metrics.append(
            ModelStringMetric(key=key, value=value, description=description)
        )

    def add_numeric_metric(
        self,
        key: str,
        value: int | float,
        unit: str | None = None,
        description: str | None = None,
    ) -> None:
        """Add a numeric metric."""
        self.numeric_metrics.append(
            ModelNumericMetric(key=key, value=value, unit=unit, description=description)
        )

    def add_boolean_metric(
        self, key: str, value: bool, description: str | None = None
    ) -> None:
        """Add a boolean metric."""
        self.boolean_metrics.append(
            ModelBooleanMetric(key=key, value=value, description=description)
        )

    def get_metric_by_key(self, key: str) -> Any | None:
        """Get metric value by key."""
        # Search string metrics
        for metric in self.string_metrics:
            if metric.key == key:
                return metric.value

        # Search numeric metrics
        for metric in self.numeric_metrics:
            if metric.key == key:
                return metric.value

        # Search boolean metrics
        for metric in self.boolean_metrics:
            if metric.key == key:
                return metric.value

        return None

    def get_all_keys(self) -> list[str]:
        """Get all metric keys."""
        keys = []
        keys.extend([m.key for m in self.string_metrics])
        keys.extend([m.key for m in self.numeric_metrics])
        keys.extend([m.key for m in self.boolean_metrics])
        return keys

    @classmethod
    def from_legacy_dict(
        cls,
        data: dict[str, str | int | bool | float],
        collection_name: str | None = None,
    ) -> "ModelMetricsData":
        """
        Create from legacy dict data for migration.

        This method helps migrate from the horrible union type to clean model.
        """
        instance = cls(collection_name=collection_name)

        for key, value in data.items():
            if isinstance(value, str):
                instance.add_string_metric(key, value)
            elif isinstance(value, (int, float)):
                instance.add_numeric_metric(key, value)
            elif isinstance(value, bool):
                instance.add_boolean_metric(key, value)

        return instance

    def to_legacy_dict(self) -> dict[str, str | int | bool | float]:
        """Convert back to legacy dict format for compatibility."""
        result = {}

        for metric in self.string_metrics:
            result[metric.key] = metric.value

        for metric in self.numeric_metrics:
            result[metric.key] = metric.value

        for metric in self.boolean_metrics:
            result[metric.key] = metric.value

        return result


# Export the models
__all__ = [
    "ModelMetricsData",
    "ModelStringMetric",
    "ModelNumericMetric",
    "ModelBooleanMetric",
]
