"""
Model for service dependency.

Service dependency status for monitoring.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.monitoring.enum_system_health import EnumSystemHealth


class ModelServiceDependency(BaseModel):
    """Service dependency status."""

    service_name: str = Field(..., description="Service name")
    status: EnumSystemHealth = Field(..., description="Service status")
    url: str | None = Field(None, description="Service URL")
    last_check: datetime = Field(..., description="Last health check")
    response_time_ms: float = Field(
        0.0,
        ge=0,
        description="Response time in milliseconds",
    )
    error_message: str | None = Field(None, description="Error message if unhealthy")
