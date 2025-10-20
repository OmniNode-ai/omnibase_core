"""
Discovery Metric Value Model

Strongly typed metric value for discovery and health monitoring.
Distinct from core ModelMetricValue which is for generic metrics.
"""

from pydantic import BaseModel, Field


class ModelMetricValue(BaseModel):
    """Single metric value with strong typing for discovery systems."""

    name: str = Field(default=..., description="Metric name")
    value: str | int | float | bool = Field(default=..., description="Metric value")
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
