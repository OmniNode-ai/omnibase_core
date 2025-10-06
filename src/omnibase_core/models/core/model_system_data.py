from pydantic import Field

"""
System Data Model.

System information data structure.
"""

from pydantic import BaseModel, Field


class ModelSystemData(BaseModel):
    """System information data."""

    # System identifiers
    system_id: str | None = Field(default=None, description="System identifier")
    version: str | None = Field(default=None, description="System version")
    environment: str | None = Field(default=None, description="Environment name")

    # System metrics
    uptime_seconds: int | None = Field(
        default=None, description="System uptime in seconds"
    )
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: int | None = Field(default=None, description="Memory usage in MB")
    disk_usage_percent: float | None = Field(
        default=None,
        description="Disk usage percentage",
    )

    # Configuration
    node_count: int | None = Field(default=None, description="Number of active nodes")
    service_count: int | None = Field(
        default=None, description="Number of active services"
    )

    # Custom fields for extensibility
    custom_metrics: dict[str, float] | None = Field(
        default=None,
        description="Custom system metrics",
    )
    custom_info: dict[str, str] | None = Field(
        default=None,
        description="Custom system information",
    )
