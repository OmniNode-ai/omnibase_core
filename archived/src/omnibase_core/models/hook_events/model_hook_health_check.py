"""Model for hook system health check."""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelHookHealthCheck(BaseModel):
    """Health check status for the hook receiver service.

    Provides comprehensive health and status information
    about the hook system for monitoring and diagnostics.
    """

    status: str = Field(
        ...,
        description="Overall health status: healthy, degraded, unhealthy",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the health check was performed",
    )

    version: str = Field(..., description="Hook receiver service version")

    uptime_seconds: int = Field(..., description="Service uptime in seconds")

    hooks_received: int = Field(
        ...,
        description="Total number of hooks received since startup",
    )

    hooks_processed: int = Field(
        ...,
        description="Total number of hooks successfully processed",
    )

    hooks_failed: int = Field(
        ...,
        description="Total number of hooks that failed processing",
    )

    active_connections: int = Field(
        ...,
        description="Current number of active connections",
    )

    event_bus_status: str = Field(..., description="Event bus connection status")

    postgres_status: str = Field(..., description="PostgreSQL connection status")

    last_hook_received: datetime | None = Field(
        None,
        description="Timestamp of the last hook received",
    )

    error_rate_percent: float = Field(
        ...,
        description="Current error rate as a percentage",
    )

    avg_processing_time_ms: float = Field(
        ...,
        description="Average hook processing time in milliseconds",
    )

    dependencies: dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services",
    )

    recent_errors: list[str] = Field(
        default_factory=list,
        description="Recent error messages for diagnostics",
    )
