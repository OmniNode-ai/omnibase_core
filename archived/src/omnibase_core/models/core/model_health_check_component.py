"""
Health check component model for individual component status.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


class ModelHealthCheckComponent(BaseModel):
    """Individual component health status."""

    name: str = Field(..., description="Component name")
    status: str = Field(
        ...,
        description="Component status (healthy/unhealthy/degraded)",
    )
    message: str | None = Field(None, description="Status message")
    last_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last check time",
    )
    response_time_ms: float | None = Field(
        None,
        description="Response time in milliseconds",
    )

    @field_serializer("last_check")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
