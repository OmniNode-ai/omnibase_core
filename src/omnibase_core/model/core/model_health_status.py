"""
Core model for health status information.

Structured model for health status, used by health check mixins
and monitoring systems throughout ONEX.
"""

from omnibase.enums.enum_health_status import EnumHealthStatus
from pydantic import BaseModel, Field

from omnibase_core.model.core.model_health_details import ModelHealthDetails


class ModelHealthStatus(BaseModel):
    """
    Structured model for health status information.

    Used by health check mixins and monitoring systems.
    """

    status: EnumHealthStatus = Field(description="Overall health status")
    message: str | None = Field(None, description="Human-readable status message")
    timestamp: str | None = Field(None, description="Timestamp of health check")
    details: ModelHealthDetails = Field(
        default_factory=ModelHealthDetails,
        description="Additional health details",
    )
    uptime_seconds: float | None = Field(
        None,
        description="System uptime in seconds",
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")
