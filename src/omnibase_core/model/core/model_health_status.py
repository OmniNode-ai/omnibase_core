"""
Core model for health status information.

Structured model for health status, used by health check mixins
and monitoring systems throughout ONEX.
"""

from typing import Optional

from omnibase.enums.enum_health_status import EnumHealthStatus
from pydantic import BaseModel, Field

from omnibase_core.model.core.model_health_details import ModelHealthDetails


class ModelHealthStatus(BaseModel):
    """
    Structured model for health status information.

    Used by health check mixins and monitoring systems.
    """

    status: EnumHealthStatus = Field(description="Overall health status")
    message: Optional[str] = Field(None, description="Human-readable status message")
    timestamp: Optional[str] = Field(None, description="Timestamp of health check")
    details: ModelHealthDetails = Field(
        default_factory=ModelHealthDetails, description="Additional health details"
    )
    uptime_seconds: Optional[float] = Field(
        None, description="System uptime in seconds"
    )
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
