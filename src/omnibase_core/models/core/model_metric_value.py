from typing import Any

from pydantic import Field

"""
Individual metric value model with metadata.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


class ModelMetricValue(BaseModel):
    """Individual metric value with metadata."""

    value: int | float | str | bool = Field(..., description="Metric value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    timestamp: datetime | None = Field(
        default=None,
        description="When the metric was captured",
    )
    labels: dict[str, str] | None = Field(
        default_factory=dict,
        description="Metric labels",
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, value) -> None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
