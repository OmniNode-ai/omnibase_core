"""
Individual metric value model with metadata.
"""

from datetime import datetime
from typing import Dict, Optional, Union

from pydantic import BaseModel, Field, field_serializer


class ModelMetricValue(BaseModel):
    """Individual metric value with metadata."""

    value: Union[int, float, str, bool] = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    timestamp: Optional[datetime] = Field(
        None, description="When the metric was captured"
    )
    labels: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Metric labels"
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
