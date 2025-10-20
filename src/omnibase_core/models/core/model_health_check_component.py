from typing import Any

from pydantic import Field

"""
Health check component model for individual component status.
"""

from datetime import datetime

from pydantic import BaseModel, field_serializer


class ModelHealthCheckComponent(BaseModel):
    """Individual component health status."""

    name: str = Field(default=..., description="Component name")
    status: str = Field(
        default=...,
        description="Component status (healthy/unhealthy/degraded)",
    )
    message: str | None = Field(default=None, description="Status message")
    last_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last check time",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Response time in milliseconds",
    )

    @field_serializer("last_check")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
