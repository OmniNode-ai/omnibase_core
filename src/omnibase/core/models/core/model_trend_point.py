"""
Trend data point model for time series data.
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, field_serializer


class ModelTrendPoint(BaseModel):
    """Individual trend data point."""

    timestamp: datetime = Field(..., description="Data point timestamp")
    value: Union[float, int] = Field(..., description="Data point value")
    label: Optional[str] = Field(None, description="Optional label")

    @field_serializer("timestamp")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
