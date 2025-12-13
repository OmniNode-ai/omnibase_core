"""
Resource Limits Model

Type-safe resource limits configuration for environments and execution contexts.
"""

from pydantic import BaseModel, Field


class ModelResourceLimits(BaseModel):
    """
    Type-safe resource limits configuration.

    This model provides structured resource limits for CPU, memory, storage,
    and other system resources.
    """

    cpu_cores: float | None = Field(
        default=None,
        description="CPU core limit (e.g., 2.5 cores)",
        ge=0.1,
        le=1000.0,
    )

    memory_mb: int | None = Field(
        default=None,
        description="Memory limit in megabytes",
        ge=1,
        le=1048576,  # 1TB max
    )

    storage_gb: float | None = Field(
        default=None,
        description="Storage limit in gigabytes",
        ge=0.1,
        le=100000.0,  # 100TB max
    )

    max_file_descriptors: int | None = Field(
        default=None,
        description="Maximum number of open file descriptors",
        ge=10,
        le=1000000,
    )

    max_processes: int | None = Field(
        default=None,
        description="Maximum number of processes",
        ge=1,
        le=100000,
    )

    max_threads: int | None = Field(
        default=None,
        description="Maximum number of threads",
        ge=1,
        le=100000,
    )

    network_bandwidth_mbps: float | None = Field(
        default=None,
        description="Network bandwidth limit in megabits per second",
        ge=0.1,
        le=100000.0,  # 100Gbps max
    )

    max_connections: int | None = Field(
        default=None,
        description="Maximum number of network connections",
        ge=1,
        le=1000000,
    )

    max_requests_per_second: float | None = Field(
        default=None,
        description="Maximum requests per second",
        ge=0.1,
        le=1000000.0,
    )

    execution_time_seconds: int | None = Field(
        default=None,
        description="Maximum execution time in seconds",
        ge=1,
        le=86400,  # 24 hours max
    )

    queue_size: int | None = Field(
        default=None,
        description="Maximum queue size for pending operations",
        ge=1,
        le=1000000,
    )

    max_retries: int | None = Field(
        default=None,
        description="Maximum number of retries for failed operations",
        ge=0,
        le=100,
    )

    def has_cpu_limit(self) -> bool:
        """Check if CPU limit is set."""
        return self.cpu_cores is not None

    def has_memory_limit(self) -> bool:
        """Check if memory limit is set."""
        return self.memory_mb is not None

    def has_storage_limit(self) -> bool:
        """Check if storage limit is set."""
        return self.storage_gb is not None

    def has_network_limit(self) -> bool:
        """Check if network bandwidth limit is set."""
        return self.network_bandwidth_mbps is not None

    def get_memory_gb(self) -> float | None:
        """Get memory limit in gigabytes."""
        if self.memory_mb is None:
            return None
        return self.memory_mb / 1024.0

    def get_storage_mb(self) -> float | None:
        """Get storage limit in megabytes."""
        if self.storage_gb is None:
            return None
        return self.storage_gb * 1024.0

    def is_constrained(self) -> bool:
        """Check if any resource limits are set."""
        return any(
            [
                self.cpu_cores is not None,
                self.memory_mb is not None,
                self.storage_gb is not None,
                self.max_file_descriptors is not None,
                self.max_processes is not None,
                self.max_threads is not None,
                self.network_bandwidth_mbps is not None,
                self.max_connections is not None,
                self.max_requests_per_second is not None,
                self.execution_time_seconds is not None,
                self.queue_size is not None,
                self.max_retries is not None,
            ],
        )
