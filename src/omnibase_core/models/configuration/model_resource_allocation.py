"""
Resource Allocation Model.

Resource allocation configuration for execution priorities.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_custom_resource_limits import (
    ModelCustomResourceLimits,
)


class ModelResourceAllocation(BaseModel):
    """
    Resource allocation configuration for execution priorities

    Defines how computational resources should be allocated for different
    priority levels, including CPU shares, memory limits, and I/O quotas.
    """

    cpu_shares: int = Field(
        default=...,
        description="CPU shares allocated (relative weight)",
        ge=1,
        le=1000,
    )

    memory_limit_mb: int | None = Field(
        default=None,
        description="Memory limit in megabytes",
        ge=1,
    )

    io_priority: int = Field(
        default=4,
        description="I/O priority level (1=highest, 7=lowest)",
        ge=1,
        le=7,
    )

    max_concurrent_tasks: int | None = Field(
        default=None,
        description="Maximum concurrent tasks for this priority",
        ge=1,
    )

    resource_guarantee: bool = Field(
        default=False,
        description="Whether resources are guaranteed (reserved)",
    )

    burst_allowance: bool = Field(
        default=True,
        description="Allow bursting above allocated resources",
    )

    custom_limits: ModelCustomResourceLimits = Field(
        default_factory=lambda: ModelCustomResourceLimits(),
        description="Custom resource limits for specific resources",
    )

    def get_total_weight(self) -> int:
        """Calculate total resource weight for scheduling"""
        base_weight = self.cpu_shares
        if self.resource_guarantee:
            base_weight *= 2  # Double weight for guaranteed resources
        if not self.burst_allowance:
            base_weight = int(base_weight * 0.8)  # Reduce weight if no bursting
        return base_weight

    def can_allocate_to(
        self,
        requested_cpu: int,
        requested_memory_mb: int | None = None,
    ) -> bool:
        """
        Check if this allocation can satisfy a resource request

        Args:
            requested_cpu: Requested CPU shares
            requested_memory_mb: Requested memory in MB

        Returns:
            True if allocation can satisfy the request
        """
        if requested_cpu > self.cpu_shares and not self.burst_allowance:
            return False

        if requested_memory_mb and self.memory_limit_mb:
            if requested_memory_mb > self.memory_limit_mb and not self.burst_allowance:
                return False

        return True

    @classmethod
    def create_dedicated(cls) -> "ModelResourceAllocation":
        """Create dedicated resource allocation (realtime priority)"""
        return cls(
            cpu_shares=1000,  # Maximum CPU shares
            memory_limit_mb=None,  # No memory limit
            io_priority=1,  # Highest I/O priority
            max_concurrent_tasks=1,  # Single task execution
            resource_guarantee=True,
            burst_allowance=False,  # No bursting needed for dedicated
        )

    @classmethod
    def create_high(cls) -> "ModelResourceAllocation":
        """Create high priority resource allocation"""
        return cls(
            cpu_shares=800,
            memory_limit_mb=None,  # No memory limit
            io_priority=2,
            max_concurrent_tasks=5,
            resource_guarantee=True,
            burst_allowance=True,
        )

    @classmethod
    def create_normal(cls) -> "ModelResourceAllocation":
        """Create normal priority resource allocation"""
        return cls(
            cpu_shares=500,
            memory_limit_mb=4096,  # 4GB memory limit
            io_priority=4,  # Default I/O priority
            max_concurrent_tasks=10,
            resource_guarantee=False,
            burst_allowance=True,
        )

    @classmethod
    def create_low(cls) -> "ModelResourceAllocation":
        """Create low priority resource allocation"""
        return cls(
            cpu_shares=200,
            memory_limit_mb=2048,  # 2GB memory limit
            io_priority=6,
            max_concurrent_tasks=20,
            resource_guarantee=False,
            burst_allowance=False,
        )

    @classmethod
    def create_batch(cls) -> "ModelResourceAllocation":
        """Create batch priority resource allocation"""
        return cls(
            cpu_shares=100,  # Lowest CPU shares
            memory_limit_mb=1024,  # 1GB memory limit
            io_priority=7,  # Lowest I/O priority
            max_concurrent_tasks=None,  # No limit on concurrent batch tasks
            resource_guarantee=False,
            burst_allowance=False,
        )

    @classmethod
    def create_custom(cls, priority_value: int) -> "ModelResourceAllocation":
        """
        Create custom resource allocation based on priority value

        Args:
            priority_value: Priority value (0-100) to scale resources

        Returns:
            Custom resource allocation
        """
        # Scale CPU shares based on priority (100-1000 range)
        cpu_shares = max(100, min(1000, priority_value * 10))

        # Scale memory limit based on priority (1GB-8GB range)
        memory_limit = max(1024, min(8192, priority_value * 80))

        # Scale I/O priority (inverse relationship)
        io_priority = max(1, min(7, 8 - (priority_value // 15)))

        # Scale max concurrent tasks
        max_tasks = max(1, min(50, (100 - priority_value) // 5 + 1))

        return cls(
            cpu_shares=cpu_shares,
            memory_limit_mb=memory_limit,
            io_priority=io_priority,
            max_concurrent_tasks=max_tasks,
            resource_guarantee=priority_value >= 80,  # Guarantee for high priorities
            burst_allowance=priority_value
            >= 30,  # Allow bursting for medium+ priorities
        )
