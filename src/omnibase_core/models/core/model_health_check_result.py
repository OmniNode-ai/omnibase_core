from pydantic import Field

from omnibase_core.types.type_serializable_value import SerializedDict

"\nHealth check result model to replace Dict[str, Any] usage for health checks.\n"
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from omnibase_core.models.core.model_health_check_component import (
    ModelHealthCheckComponent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

HealthCheckComponent = ModelHealthCheckComponent


class ModelHealthCheckResult(BaseModel):
    """
    Health check result with typed fields.
    Replaces Dict[str, Any] for health_check() returns.
    """

    status: str = Field(
        default=..., description="Overall health status (healthy/unhealthy/degraded)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Check timestamp"
    )
    components: list[ModelHealthCheckComponent] = Field(
        default_factory=list, description="Individual component statuses"
    )
    service_name: str = Field(default=..., description="Service name")
    service_version: ModelSemVer | None = Field(
        default=None, description="Service version"
    )
    uptime_seconds: int | None = Field(
        default=None, description="Service uptime in seconds"
    )
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )
    disk_usage_gb: float | None = Field(default=None, description="Disk usage in GB")
    database_connected: bool | None = Field(
        default=None, description="Database connection status"
    )
    cache_connected: bool | None = Field(
        default=None, description="Cache connection status"
    )
    queue_connected: bool | None = Field(
        default=None, description="Queue connection status"
    )
    average_response_time_ms: float | None = Field(
        default=None, description="Average response time"
    )
    requests_per_second: float | None = Field(
        default=None, description="Current requests per second"
    )
    error_rate: float | None = Field(default=None, description="Error rate percentage")
    checks_passed: int = Field(default=0, description="Number of checks passed")
    checks_failed: int = Field(default=0, description="Number of checks failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @classmethod
    def from_dict(cls, data: SerializedDict) -> "ModelHealthCheckResult":
        """Create from dictionary for easy migration."""
        return cls.model_validate(data)

    @property
    def is_healthy(self) -> bool:
        """Check if overall status is healthy."""
        return self.status.lower() == "healthy"

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
