"""
Trend data point model for time series data.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


class ModelTrendPoint(BaseModel):
    """Individual trend data point."""

    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float | int = Field(..., description="Data point value")
    label: str | None = Field(None, description="Optional label")

    @field_serializer("timestamp")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
