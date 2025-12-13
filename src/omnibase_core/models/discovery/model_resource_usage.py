"""
Resource Usage Model

Model for current resource usage information.
"""

from pydantic import BaseModel, Field


class ModelResourceUsage(BaseModel):
    """Current resource usage information"""

    cpu_percent: float | None = Field(
        default=None,
        description="Current CPU usage percentage (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )
    memory_mb: float | None = Field(
        default=None,
        description="Current memory usage in megabytes",
        ge=0.0,
    )
    memory_percent: float | None = Field(
        default=None,
        description="Current memory usage percentage (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )
    disk_usage_percent: float | None = Field(
        default=None,
        description="Current disk usage percentage (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )
    open_files: int | None = Field(
        default=None,
        description="Number of open file descriptors",
        ge=0,
    )
    active_connections: int | None = Field(
        default=None,
        description="Number of active network connections",
        ge=0,
    )
