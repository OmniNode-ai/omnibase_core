import logging

from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_metric_value import (
    AnyMetricValue,
    ModelMetricValue,
)
from omnibase_core.types.type_json import PrimitiveValue

logger = logging.getLogger(__name__)


class ModelCustomMetrics(BaseModel):
    """Custom metrics container with strong typing."""

    metrics: list[AnyMetricValue] = Field(
        default_factory=list,
        description="List of typed custom metrics",
    )

    def get_metrics_dict(self) -> dict[str, PrimitiveValue]:
        """Convert to dictionary format."""
        return {metric.name: metric.value for metric in self.metrics}

    @classmethod
    def from_dict(
        cls,
        metrics_dict: dict[str, PrimitiveValue],
    ) -> "ModelCustomMetrics":
        """Create from dictionary with type inference."""
        metrics: list[AnyMetricValue] = []
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
            else:
                # Defensive fallback for unexpected types at runtime
                # Type annotation guarantees exhaustiveness, but runtime may differ
                logger.warning(  # type: ignore[unreachable]
                    "Unexpected metric type %s for metric '%s', converting to string",
                    type(value).__name__,
                    name,
                )
                metric_type = "string"
                value = str(value)

            metrics.append(
                ModelMetricValue(name=name, value=value, metric_type=metric_type),
            )

        return cls(metrics=metrics)
