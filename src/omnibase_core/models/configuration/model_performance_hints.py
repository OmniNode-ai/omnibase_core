"""
Performance Hints Model.

Type-safe performance optimization hints for node operations
and load balancing decisions.
"""

from pydantic import BaseModel, Field


class ModelPerformanceHints(BaseModel):
    """
    Performance optimization hints for nodes.

    Provides structured performance information to help with
    load balancing and optimization decisions.
    """

    cpu_intensive: bool = Field(
        default=False,
        description="Whether operations are CPU intensive",
    )
    memory_intensive: bool = Field(
        default=False,
        description="Whether operations are memory intensive",
    )
    io_intensive: bool = Field(
        default=False,
        description="Whether operations are I/O intensive",
    )
    network_intensive: bool = Field(
        default=False,
        description="Whether operations are network intensive",
    )
    preferred_batch_size: int | None = Field(
        default=None,
        description="Preferred batch size for operations",
        ge=1,
        le=10000,
    )
    max_concurrent_operations: int | None = Field(
        default=None,
        description="Maximum concurrent operations",
        ge=1,
        le=1000,
    )
    cache_friendly: bool = Field(
        default=True,
        description="Whether operations benefit from caching",
    )
    stateless: bool = Field(
        default=True,
        description="Whether operations are stateless",
    )
    warm_up_time_ms: int | None = Field(
        default=None,
        description="Time needed for warm-up in milliseconds",
        ge=0,
    )

    def is_resource_intensive(self) -> bool:
        """Check if node has any resource-intensive characteristics."""
        return any(
            [
                self.cpu_intensive,
                self.memory_intensive,
                self.io_intensive,
                self.network_intensive,
            ],
        )
