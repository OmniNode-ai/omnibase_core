from typing import List

from pydantic import BaseModel, Field


class ModelCustomMetrics(BaseModel):
    """Custom metrics container with strong typing."""

    metrics: list[ModelMetricValue] = Field(
        default_factory=list,
        description="List of typed custom metrics",
    )

    def get_metrics_dict(self) -> dict[str, str | int | float | bool]:
        """Convert to dict[str, Any]ionary format."""
        return {metric.name: metric.value for metric in self.metrics}

    @classmethod
    def from_dict(
        cls,
        metrics_dict: dict[str, str | int | float | bool],
    ) -> "ModelCustomMetrics":
        """Create from dict[str, Any]ionary with type inference."""
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
