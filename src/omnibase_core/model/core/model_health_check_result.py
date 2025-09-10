"""
Health check result model to replace Dict[str, Any] usage for health checks.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.model.core.model_health_check_component import (
    ModelHealthCheckComponent,
)

# Backward compatibility alias
HealthCheckComponent = ModelHealthCheckComponent


class ModelHealthCheckResult(BaseModel):
    """
    Health check result with typed fields.
    Replaces Dict[str, Any] for health_check() returns.
    """

    # Overall status
    status: str = Field(
        ...,
        description="Overall health status (healthy/unhealthy/degraded)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Check timestamp",
    )

    # Component statuses
    components: list[ModelHealthCheckComponent] = Field(
        default_factory=list,
        description="Individual component statuses",
    )

    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str | None = Field(None, description="Service version")
    uptime_seconds: int | None = Field(None, description="Service uptime in seconds")

    # Resource usage
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    disk_usage_gb: float | None = Field(None, description="Disk usage in GB")

    # Connection status
    database_connected: bool | None = Field(
        None,
        description="Database connection status",
    )
    cache_connected: bool | None = Field(None, description="Cache connection status")
    queue_connected: bool | None = Field(None, description="Queue connection status")

    # Performance metrics
    average_response_time_ms: float | None = Field(
        None,
        description="Average response time",
    )
    requests_per_second: float | None = Field(
        None,
        description="Current requests per second",
    )
    error_rate: float | None = Field(None, description="Error rate percentage")

    # Additional checks
    checks_passed: int = Field(0, description="Number of checks passed")
    checks_failed: int = Field(0, description="Number of checks failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")

    model_config = ConfigDict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelHealthCheckResult":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @property
    def is_healthy(self) -> bool:
        """Check if overall status is healthy."""
        return self.status.lower() == "healthy"

    @field_serializer("timestamp")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
