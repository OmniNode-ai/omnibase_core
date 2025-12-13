"""
Model for resource usage details.

Structured model for resource usage details, replacing Dict[str, Any]
with proper typing for resource usage.
"""

from pydantic import BaseModel, Field


class ModelResourceUsageDetails(BaseModel):
    """
    Structured model for resource usage details.

    Replaces Dict[str, Any] with proper typing for resource usage.
    """

    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )
    disk_io_mb: float | None = Field(default=None, description="Disk I/O in MB")
    network_io_mb: float | None = Field(default=None, description="Network I/O in MB")
    file_handles: int | None = Field(
        default=None, description="Number of open file handles"
    )
    thread_count: int | None = Field(
        default=None, description="Number of active threads"
    )
    connection_count: int | None = Field(
        default=None,
        description="Number of active connections",
    )
    temp_files_created: int | None = Field(
        default=None,
        description="Number of temporary files created",
    )
    peak_memory_mb: float | None = Field(
        default=None, description="Peak memory usage in MB"
    )
    gc_collections: int | None = Field(
        default=None,
        description="Number of garbage collections",
    )
