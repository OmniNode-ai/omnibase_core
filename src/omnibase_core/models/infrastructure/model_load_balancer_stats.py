"""Model for load balancer statistics."""

from pydantic import BaseModel, ConfigDict, Field


class ModelLoadBalancerStats(BaseModel):
    """
    Strongly-typed model for load balancer statistics.

    This model represents the statistics returned by the LoadBalancer.get_stats()
    method, providing structured information about current load balancing state.

    Attributes:
        active_operations: Number of currently active operations
        max_concurrent: Maximum allowed concurrent operations
        utilization: Current utilization ratio (active/max)
        total_operations: Total number of operations processed
    """

    active_operations: int = Field(
        default=0,
        ge=0,
        description="Number of currently active operations",
    )
    max_concurrent: int = Field(
        default=10,
        ge=1,
        description="Maximum allowed concurrent operations",
    )
    utilization: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current utilization ratio (active/max)",
    )
    total_operations: int = Field(
        default=0,
        ge=0,
        description="Total number of operations processed",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
