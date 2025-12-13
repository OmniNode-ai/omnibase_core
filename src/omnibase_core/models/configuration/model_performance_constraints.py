"""
Performance Constraints Model.

Type-safe performance constraints for execution capabilities
and resource management.
"""

from pydantic import BaseModel, Field


class ModelPerformanceConstraints(BaseModel):
    """
    Performance constraints configuration.

    Provides structured performance constraints for execution
    capabilities and resource management decisions.
    """

    max_memory_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in MB",
        ge=1,
    )
    max_cpu_cores: float | None = Field(
        default=None,
        description="Maximum CPU cores",
        ge=0.1,
        le=64.0,
    )
    max_disk_io_mb_per_sec: int | None = Field(
        default=None,
        description="Maximum disk I/O in MB/sec",
        ge=1,
    )
    max_network_mb_per_sec: int | None = Field(
        default=None,
        description="Maximum network bandwidth in MB/sec",
        ge=1,
    )
    max_execution_time_ms: int | None = Field(
        default=None,
        description="Maximum execution time in milliseconds",
        ge=1,
    )
    max_queue_size: int | None = Field(
        default=None, description="Maximum queue size", ge=1
    )
    priority_class: str = Field(
        default="normal",
        description="Priority class for resource allocation",
        pattern="^(low|normal|high|critical)$",
    )
    preemptible: bool = Field(
        default=True,
        description="Whether execution can be preempted",
    )

    def is_within_limits(self, memory_mb: int, cpu_cores: float) -> bool:
        """Check if resource usage is within constraints."""
        if self.max_memory_mb and memory_mb > self.max_memory_mb:
            return False

        return not (self.max_cpu_cores and cpu_cores > self.max_cpu_cores)

    def get_priority_weight(self) -> float:
        """Get numeric priority weight for scheduling."""
        priority_weights = {"low": 0.25, "normal": 1.0, "high": 2.0, "critical": 4.0}
        return priority_weights.get(self.priority_class, 1.0)
