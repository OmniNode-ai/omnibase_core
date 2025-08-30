"""
Resource allocation model to replace Dict[str, Any] usage for resource specifications.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.core.model_resource_limit import ModelResourceLimit

# Backward compatibility alias
ResourceLimit = ModelResourceLimit


class ModelResourceAllocation(BaseModel):
    """
    Resource allocation specification with typed fields.
    Replaces Dict[str, Any] for resource_allocation fields.
    """

    # CPU resources
    cpu_cores: Optional[float] = Field(None, description="Number of CPU cores")
    cpu_limit: Optional[ModelResourceLimit] = Field(
        None, description="CPU usage limits"
    )
    cpu_shares: Optional[int] = Field(None, description="CPU shares for scheduling")

    # Memory resources
    memory_mb: Optional[float] = Field(None, description="Memory in megabytes")
    memory_limit: Optional[ModelResourceLimit] = Field(
        None, description="Memory usage limits"
    )
    memory_swap_mb: Optional[float] = Field(
        None, description="Swap memory in megabytes"
    )

    # Storage resources
    disk_gb: Optional[float] = Field(None, description="Disk space in gigabytes")
    disk_iops: Optional[int] = Field(None, description="Disk IOPS limit")
    disk_throughput_mb: Optional[float] = Field(
        None, description="Disk throughput in MB/s"
    )

    # Network resources
    network_bandwidth_mbps: Optional[float] = Field(
        None, description="Network bandwidth in Mbps"
    )
    network_connections: Optional[int] = Field(
        None, description="Max network connections"
    )

    # GPU resources (if applicable)
    gpu_count: Optional[int] = Field(None, description="Number of GPUs")
    gpu_memory_mb: Optional[float] = Field(None, description="GPU memory per device")
    gpu_compute_units: Optional[int] = Field(None, description="GPU compute units")

    # Queue/Thread resources
    max_threads: Optional[int] = Field(None, description="Maximum thread count")
    max_processes: Optional[int] = Field(None, description="Maximum process count")
    queue_size: Optional[int] = Field(None, description="Maximum queue size")

    # Time-based resources
    execution_timeout_seconds: Optional[int] = Field(
        None, description="Execution timeout"
    )
    idle_timeout_seconds: Optional[int] = Field(None, description="Idle timeout")

    # Priority and scheduling
    priority: Optional[int] = Field(None, description="Resource allocation priority")
    scheduling_class: Optional[str] = Field(None, description="Scheduling class")

    # Resource tags and metadata
    resource_tags: Dict[str, str] = Field(
        default_factory=dict, description="Resource tags for grouping/billing"
    )

    # Scaling policies
    auto_scaling_enabled: Optional[bool] = Field(
        None, description="Enable auto-scaling"
    )
    scale_up_threshold: Optional[float] = Field(None, description="Scale up threshold")
    scale_down_threshold: Optional[float] = Field(
        None, description="Scale down threshold"
    )

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional fields for extensibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["ModelResourceAllocation"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)
