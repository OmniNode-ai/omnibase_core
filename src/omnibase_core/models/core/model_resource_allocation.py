"""
Resource allocation model to replace Dict[str, Any] usage for resource specifications.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_resource_limit import ModelResourceLimit

# Compatibility alias
ResourceLimit = ModelResourceLimit


class ModelResourceAllocation(BaseModel):
    """
    Resource allocation specification with typed fields.
    Replaces Dict[str, Any] for resource_allocation fields.
    """

    # CPU resources
    cpu_cores: float | None = Field(None, description="Number of CPU cores")
    cpu_limit: ModelResourceLimit | None = Field(
        None,
        description="CPU usage limits",
    )
    cpu_shares: int | None = Field(None, description="CPU shares for scheduling")

    # Memory resources
    memory_mb: float | None = Field(None, description="Memory in megabytes")
    memory_limit: ModelResourceLimit | None = Field(
        None,
        description="Memory usage limits",
    )
    memory_swap_mb: float | None = Field(
        None,
        description="Swap memory in megabytes",
    )

    # Storage resources
    disk_gb: float | None = Field(None, description="Disk space in gigabytes")
    disk_iops: int | None = Field(None, description="Disk IOPS limit")
    disk_throughput_mb: float | None = Field(
        None,
        description="Disk throughput in MB/s",
    )

    # Network resources
    network_bandwidth_mbps: float | None = Field(
        None,
        description="Network bandwidth in Mbps",
    )
    network_connections: int | None = Field(
        None,
        description="Max network connections",
    )

    # GPU resources (if applicable)
    gpu_count: int | None = Field(None, description="Number of GPUs")
    gpu_memory_mb: float | None = Field(None, description="GPU memory per device")
    gpu_compute_units: int | None = Field(None, description="GPU compute units")

    # Queue/Thread resources
    max_threads: int | None = Field(None, description="Maximum thread count")
    max_processes: int | None = Field(None, description="Maximum process count")
    queue_size: int | None = Field(None, description="Maximum queue size")

    # Time-based resources
    execution_timeout_seconds: int | None = Field(
        None,
        description="Execution timeout",
    )
    idle_timeout_seconds: int | None = Field(None, description="Idle timeout")

    # Priority and scheduling
    priority: int | None = Field(None, description="Resource allocation priority")
    scheduling_class: str | None = Field(None, description="Scheduling class")

    # Resource tags and metadata
    resource_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Resource tags for grouping/billing",
    )

    # Scaling policies
    auto_scaling_enabled: bool | None = Field(
        None,
        description="Enable auto-scaling",
    )
    scale_up_threshold: float | None = Field(None, description="Scale up threshold")
    scale_down_threshold: float | None = Field(
        None,
        description="Scale down threshold",
    )

    model_config = ConfigDict(
        extra="allow",
    )  # Allow additional fields for extensibility

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelResourceAllocation"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)
