"""
Resource Limits Model

Type-safe resource limits configuration for environments and execution contexts.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelResourceLimits(BaseModel):
    """
    Type-safe resource limits configuration.

    This model provides structured resource limits for CPU, memory, storage,
    and other system resources.
    """

    cpu_cores: Optional[float] = Field(
        None, description="CPU core limit (e.g., 2.5 cores)", ge=0.1, le=1000.0
    )

    memory_mb: Optional[int] = Field(
        None, description="Memory limit in megabytes", ge=1, le=1048576  # 1TB max
    )

    storage_gb: Optional[float] = Field(
        None, description="Storage limit in gigabytes", ge=0.1, le=100000.0  # 100TB max
    )

    max_file_descriptors: Optional[int] = Field(
        None, description="Maximum number of open file descriptors", ge=10, le=1000000
    )

    max_processes: Optional[int] = Field(
        None, description="Maximum number of processes", ge=1, le=100000
    )

    max_threads: Optional[int] = Field(
        None, description="Maximum number of threads", ge=1, le=100000
    )

    network_bandwidth_mbps: Optional[float] = Field(
        None,
        description="Network bandwidth limit in megabits per second",
        ge=0.1,
        le=100000.0,  # 100Gbps max
    )

    max_connections: Optional[int] = Field(
        None, description="Maximum number of network connections", ge=1, le=1000000
    )

    max_requests_per_second: Optional[float] = Field(
        None, description="Maximum requests per second", ge=0.1, le=1000000.0
    )

    execution_time_seconds: Optional[int] = Field(
        None,
        description="Maximum execution time in seconds",
        ge=1,
        le=86400,  # 24 hours max
    )

    queue_size: Optional[int] = Field(
        None, description="Maximum queue size for pending operations", ge=1, le=1000000
    )

    max_retries: Optional[int] = Field(
        None,
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

    def get_memory_gb(self) -> Optional[float]:
        """Get memory limit in gigabytes."""
        if self.memory_mb is None:
            return None
        return self.memory_mb / 1024.0

    def get_storage_mb(self) -> Optional[float]:
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
            ]
        )

    @classmethod
    def create_minimal(cls) -> "ModelResourceLimits":
        """Create minimal resource limits for development."""
        return cls(
            cpu_cores=1.0,
            memory_mb=512,
            storage_gb=1.0,
            max_connections=100,
            max_requests_per_second=10.0,
        )

    @classmethod
    def create_standard(cls) -> "ModelResourceLimits":
        """Create standard resource limits."""
        return cls(
            cpu_cores=2.0,
            memory_mb=2048,
            storage_gb=10.0,
            max_connections=1000,
            max_requests_per_second=100.0,
            max_processes=100,
            max_threads=1000,
        )

    @classmethod
    def create_high_performance(cls) -> "ModelResourceLimits":
        """Create high performance resource limits."""
        return cls(
            cpu_cores=8.0,
            memory_mb=16384,
            storage_gb=100.0,
            max_connections=10000,
            max_requests_per_second=1000.0,
            max_processes=1000,
            max_threads=10000,
            network_bandwidth_mbps=1000.0,
        )

    @classmethod
    def create_unlimited(cls) -> "ModelResourceLimits":
        """Create unlimited resource configuration (all limits None)."""
        return cls()
