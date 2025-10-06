from pydantic import Field

"""
Service Status Model.

Status of a system service.
"""

from pydantic import BaseModel, Field


class ModelServiceStatus(BaseModel):
    """Status of a system service."""

    service_name: str = Field(..., description="Name of the service")
    service_type: str | None = Field(None, description="Type of service")
    status: str = Field(..., description="Service status (running, stopped, error)")
    health: str | None = Field(
        None,
        description="Service health (healthy, degraded, unhealthy)",
    )

    # Service details
    version: str | None = Field(None, description="Service version")
    uptime_seconds: int | None = Field(None, description="Service uptime")
    last_check: str | None = Field(None, description="Last health check timestamp")

    # Performance metrics
    response_time_ms: float | None = Field(None, description="Average response time")
    error_rate: float | None = Field(None, description="Error rate percentage")
    request_count: int | None = Field(None, description="Total request count")

    # Additional info
    message: str | None = Field(None, description="Status message")
    details: dict[str, str] | None = Field(None, description="Additional details")
