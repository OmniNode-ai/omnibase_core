"""
Node Resource Limits Model.

Resource limitation configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelNodeResourceLimits(BaseModel):
    """
    Node resource limitation settings.

    Contains resource management parameters:
    - Memory and CPU limits
    - Performance constraints
    """

    # Resource limits (2 fields)
    max_memory_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in MB",
        ge=0,
    )
    max_cpu_percent: float | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=0.0,
        le=100.0,
    )

    def has_memory_limit(self) -> bool:
        """Check if memory limit is set."""
        return self.max_memory_mb is not None

    def has_cpu_limit(self) -> bool:
        """Check if CPU limit is set."""
        return self.max_cpu_percent is not None

    def has_any_limits(self) -> bool:
        """Check if any resource limits are configured."""
        return self.has_memory_limit() or self.has_cpu_limit()

    def get_resource_summary(self) -> dict[str, int | float | bool | None]:
        """Get resource limits summary."""
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "has_memory_limit": self.has_memory_limit(),
            "has_cpu_limit": self.has_cpu_limit(),
            "has_any_limits": self.has_any_limits(),
        }

    def is_memory_constrained(self, threshold_mb: int = 1024) -> bool:
        """Check if memory is constrained below threshold."""
        return self.max_memory_mb is not None and self.max_memory_mb < threshold_mb

    def is_cpu_constrained(self, threshold_percent: float = 50.0) -> bool:
        """Check if CPU is constrained below threshold."""
        return (
            self.max_cpu_percent is not None
            and self.max_cpu_percent < threshold_percent
        )

    @classmethod
    def create_unlimited(cls) -> ModelNodeResourceLimits:
        """Create unlimited resource configuration."""
        return cls()

    @classmethod
    def create_constrained(
        cls,
        memory_mb: int | None = None,
        cpu_percent: float | None = None,
    ) -> ModelNodeResourceLimits:
        """Create constrained resource configuration."""
        return cls(
            max_memory_mb=memory_mb,
            max_cpu_percent=cpu_percent,
        )


# Export for use
__all__ = ["ModelNodeResourceLimits"]
