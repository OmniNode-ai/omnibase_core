from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_metric_value import ModelMetricValue


class ModelCustomMetrics(BaseModel):
    """Custom metrics container with strong typing."""

    metrics: list[ModelMetricValue] = Field(
        default_factory=list,
        description="List of typed custom metrics",
    )

    def get_metrics_dict(self) -> dict[str, str | int | float | bool]:
        """Convert to dictionary format."""
        return {metric.name: metric.value for metric in self.metrics}

    @classmethod
    def from_dict(
        cls,
        metrics_dict: dict[str, str | int | float | bool],
    ) -> "ModelCustomMetrics":
        """Create from dictionary with type inference."""
        metrics = []
        for name, value in metrics_dict.items():
            # Check bool before int since bool is a subclass of int in Python
            if isinstance(value, bool):
                metric_type = "boolean"
            elif isinstance(value, str):
                metric_type = "string"
            elif isinstance(value, int):
                metric_type = "integer"
            elif isinstance(value, float):
                metric_type = "float"

            metrics.append(
                ModelMetricValue(name=name, value=value, metric_type=metric_type),
            )

        return cls(metrics=metrics)
