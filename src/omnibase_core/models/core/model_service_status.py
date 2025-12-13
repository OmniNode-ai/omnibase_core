"""
Service Status Model.

Status of a system service.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelServiceStatus(BaseModel):
    """Status of a system service."""

    service_name: str = Field(default=..., description="Name of the service")
    service_type: str | None = Field(default=None, description="Type of service")
    status: str = Field(
        default=..., description="Service status (running, stopped, error)"
    )
    health: str | None = Field(
        default=None,
        description="Service health (healthy, degraded, unhealthy)",
    )

    # Service details
    version: ModelSemVer | None = Field(default=None, description="Service version")
    uptime_seconds: int | None = Field(default=None, description="Service uptime")
    last_check: str | None = Field(
        default=None, description="Last health check timestamp"
    )

    # Performance metrics
    response_time_ms: float | None = Field(
        default=None, description="Average response time"
    )
    error_rate: float | None = Field(default=None, description="Error rate percentage")
    request_count: int | None = Field(default=None, description="Total request count")

    # Additional info
    message: str | None = Field(default=None, description="Status message")
    details: dict[str, str] | None = Field(
        default=None, description="Additional details"
    )
