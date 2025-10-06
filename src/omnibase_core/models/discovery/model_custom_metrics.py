import json
from typing import Any, Dict

from pydantic import Field

from .model_custommetrics import ModelCustomMetrics

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
