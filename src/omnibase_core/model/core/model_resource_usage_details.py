"""
Model for resource usage details.

Structured model for resource usage details, replacing Dict[str, Any]
with proper typing for resource usage.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelResourceUsageDetails(BaseModel):
    """
    Structured model for resource usage details.

    Replaces Dict[str, Any] with proper typing for resource usage.
    """

    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    disk_io_mb: Optional[float] = Field(None, description="Disk I/O in MB")
    network_io_mb: Optional[float] = Field(None, description="Network I/O in MB")
    file_handles: Optional[int] = Field(None, description="Number of open file handles")
    thread_count: Optional[int] = Field(None, description="Number of active threads")
    connection_count: Optional[int] = Field(
        None, description="Number of active connections"
    )
    temp_files_created: Optional[int] = Field(
        None, description="Number of temporary files created"
    )
    peak_memory_mb: Optional[float] = Field(None, description="Peak memory usage in MB")
    gc_collections: Optional[int] = Field(
        None, description="Number of garbage collections"
    )
