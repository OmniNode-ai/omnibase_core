from uuid import UUID

from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"\nSystem Data Model.\n\nSystem information data structure.\n"
from pydantic import BaseModel


class ModelSystemData(BaseModel):
    """System information data."""

    system_id: UUID | None = Field(default=None, description="System identifier")
    version: ModelSemVer | None = Field(default=None, description="System version")
    environment: str | None = Field(default=None, description="Environment name")
    uptime_seconds: int | None = Field(
        default=None, description="System uptime in seconds"
    )
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: int | None = Field(default=None, description="Memory usage in MB")
    disk_usage_percent: float | None = Field(
        default=None, description="Disk usage percentage"
    )
    node_count: int | None = Field(default=None, description="Number of active nodes")
    service_count: int | None = Field(
        default=None, description="Number of active services"
    )
    custom_metrics: dict[str, float] | None = Field(
        default=None, description="Custom system metrics"
    )
    custom_info: dict[str, str] | None = Field(
        default=None, description="Custom system information"
    )
