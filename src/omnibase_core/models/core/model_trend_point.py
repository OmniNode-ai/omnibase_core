from pydantic import Field

"""
Trend data point model for time series data.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_serializer


class ModelTrendPoint(BaseModel):
    """Individual trend data point."""

    timestamp: datetime = Field(default=..., description="Data point timestamp")
    value: float | int = Field(default=..., description="Data point value")
    label: str | None = Field(default=None, description="Optional label")

    @field_serializer("timestamp")
    def serialize_datetime(self, value: Any) -> None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
