"""
Custom Resource Limits Model.

Custom resource limits for specific resources.
"""

from pydantic import BaseModel, Field


class ModelCustomResourceLimits(BaseModel):
    """
    Custom resource limits for specific resources.

    Allows defining limits for various resource types that may be
    platform or deployment specific.
    """

    network_bandwidth_mbps: int | None = Field(
        default=None,
        description="Network bandwidth limit in Mbps",
        ge=1,
    )

    disk_iops: int | None = Field(
        default=None,
        description="Disk I/O operations per second limit",
        ge=1,
    )

    gpu_shares: int | None = Field(
        default=None,
        description="GPU compute shares (0-100)",
        ge=0,
        le=100,
    )

    ephemeral_storage_gb: int | None = Field(
        default=None,
        description="Ephemeral storage limit in GB",
        ge=1,
    )

    max_open_files: int | None = Field(
        default=None,
        description="Maximum number of open file descriptors",
        ge=1,
    )

    max_threads: int | None = Field(
        default=None,
        description="Maximum number of threads",
        ge=1,
    )

    swap_limit_mb: int | None = Field(
        default=None,
        description="Swap memory limit in MB",
        ge=0,
    )

    cpu_quota_us: int | None = Field(
        default=None,
        description="CPU quota in microseconds per period",
        ge=1000,
    )

    cpu_period_us: int | None = Field(
        default=None,
        description="CPU quota period in microseconds",
        ge=1000,
    )
