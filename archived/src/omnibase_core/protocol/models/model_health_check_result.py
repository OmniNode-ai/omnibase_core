"""Health check result model for protocol interfaces."""

from pydantic import BaseModel, Field


class ModelHealthCheckResult(BaseModel):
    """Health check result for protocol implementations."""

    status: str = Field(..., description="Health status (healthy, unhealthy, degraded)")
    service_name: str = Field(..., description="Name of the service being checked")
    version: str | None = Field(None, description="Service version")
    timestamp: str = Field(..., description="Timestamp of health check")

    # Capabilities and features
    capabilities: list[str] = Field(
        default_factory=list,
        description="Available capabilities",
    )
    features_enabled: list[str] = Field(
        default_factory=list,
        description="Enabled features",
    )

    # Performance metrics
    uptime_seconds: float | None = Field(
        None,
        description="Service uptime in seconds",
    )
    response_time_ms: float | None = Field(
        None,
        description="Health check response time in milliseconds",
    )
    memory_usage_mb: float | None = Field(
        None,
        description="Current memory usage in MB",
    )
    cpu_usage_percent: float | None = Field(
        None,
        description="Current CPU usage percentage",
    )

    # Dependencies
    dependencies_healthy: bool = Field(
        default=True,
        description="Whether all dependencies are healthy",
    )
    dependency_status: list[str] = Field(
        default_factory=list,
        description="Status of each dependency",
    )

    # Error information
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    errors: list[str] = Field(default_factory=list, description="Error messages")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
