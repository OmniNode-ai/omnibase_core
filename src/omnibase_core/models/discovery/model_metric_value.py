"""
Discovery Metric Value Model

Strongly typed metric value for discovery and health monitoring.
Distinct from core ModelMetricValue which is for generic metrics.

This model uses Python generics for type-safe metric values.

Usage Examples:
    # Explicit type parameter for type safety at usage time:
    metric_str: ModelMetricValue[str] = ModelMetricValue(
        name="status", value="healthy", metric_type="string"
    )
    metric_int: ModelMetricValue[int] = ModelMetricValue(
        name="count", value=42, metric_type="counter"
    )

    # For collections with mixed types, use the type alias:
    metrics: dict[str, AnyMetricValue] = {
        "status": ModelMetricValue(name="status", value="ok", metric_type="string"),
        "count": ModelMetricValue(name="count", value=10, metric_type="counter"),
    }
"""

from typing import TypeVar

from pydantic import BaseModel, Field

# TypeVar exported for external use in type hints
MetricValueT = TypeVar("MetricValueT", str, int, float, bool)


class ModelMetricValue[MetricValueT: str | int | float | bool](BaseModel):
    """Single metric value with strong typing for discovery systems.

    Generic over MetricValueT which must be str, int, float, or bool.
    Provides type safety when the value type is known at usage time.

    Type Parameters:
        MetricValueT: The type of the metric value (str, int, float, or bool)

    Attributes:
        name: Metric name identifier
        value: The metric value with type safety via generic parameter
        metric_type: String describing the metric type (e.g., "string", "counter")
        unit: Optional unit of measurement (e.g., "ms", "bytes")
        tags: Optional list of tags for categorization
    """

    name: str = Field(default=..., description="Metric name")
    value: MetricValueT = Field(default=..., description="Metric value")
    metric_type: str = Field(
        default=...,
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
        default=None,
        description="Metric unit (e.g., 'ms', 'bytes', 'percent')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Metric tags for categorization",
    )


# Type alias for collections containing mixed metric value types
AnyMetricValue = ModelMetricValue[str | int | float | bool]
