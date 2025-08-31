"""
Custom Metrics Model

Strongly typed model for custom metrics to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with zero tolerance for Any types.
"""

from pydantic import BaseModel, Field


class ModelMetricValue(BaseModel):
    """Single metric value with strong typing."""

    name: str = Field(..., description="Metric name")
    value: str | int | float | bool = Field(..., description="Metric value")
    metric_type: str = Field(
        ...,
        description="Metric value type",
        json_schema_extra={
            "enum": [
                "string",
                "integer",
                "float",
                "boolean",
                "counter",
                "gauge",
                "histogram",
            ],
        },
    )
    unit: str | None = Field(
        None,
        description="Metric unit (e.g., 'ms', 'bytes', 'percent')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Metric tags for categorization",
    )


class ModelCustomMetrics(BaseModel):
    """Custom metrics container with strong typing."""

    metrics: list[ModelMetricValue] = Field(
        default_factory=list,
        description="List of typed custom metrics",
    )

    def get_metrics_dict(self) -> dict[str, str | int | float | bool]:
        """Convert to dictionary format for backward compatibility."""
        return {metric.name: metric.value for metric in self.metrics}

    @classmethod
    def from_dict(
        cls,
        metrics_dict: dict[str, str | int | float | bool],
    ) -> "ModelCustomMetrics":
        """Create from dictionary with type inference."""
        metrics = []
        for name, value in metrics_dict.items():
            if isinstance(value, str):
                metric_type = "string"
            elif isinstance(value, int):
                metric_type = "integer"
            elif isinstance(value, float):
                metric_type = "float"
            elif isinstance(value, bool):
                metric_type = "boolean"
            else:
                # Fallback to string representation
                metric_type = "string"
                value = str(value)

            metrics.append(
                ModelMetricValue(name=name, value=value, metric_type=metric_type),
            )

        return cls(metrics=metrics)
