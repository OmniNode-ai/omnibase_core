from pydantic import Field, field_validator

"""
Core model for health status information.

Structured model for health status, used by health check mixins
and monitoring systems throughout ONEX.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.models.core.model_health_details import ModelHealthDetails


class ModelHealthStatus(BaseModel):
    """
    Structured model for health status information.

    Used by health check mixins and monitoring systems.
    """

    status: EnumNodeHealthStatus = Field(description="Overall health status")
    message: str | None = Field(
        default=None, description="Human-readable status message"
    )
    timestamp: str | None = Field(default=None, description="Timestamp of health check")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> str | None:
        """
        Convert datetime objects to ISO format strings.

        Allows Pydantic to automatically handle datetime-to-string conversion
        instead of requiring manual validation.
        """
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, str):
            return v
        # For any other type, try to convert to string
        return str(v)

    details: ModelHealthDetails = Field(
        default_factory=lambda: ModelHealthDetails(),
        description="Additional health details",
    )
    uptime_seconds: float | None = Field(
        default=None,
        description="System uptime in seconds",
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
