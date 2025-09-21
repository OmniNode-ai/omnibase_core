"""
Node Execution Settings Model.

Execution-related configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelNodeExecutionSettings(BaseModel):
    """
    Node execution configuration settings.

    Contains execution-specific parameters:
    - Retry and timeout settings
    - Batch processing configuration
    - Execution mode flags
    """

    # Execution control (3 fields)
    max_retries: int | None = Field(default=None, description="Maximum retry attempts")
    timeout_seconds: int | None = Field(default=None, description="Execution timeout")
    batch_size: int | None = Field(default=None, description="Batch processing size")

    # Execution mode (1 field)
    parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution",
    )

    def get_execution_summary(self) -> dict[str, int | bool | None]:
        """Get execution settings summary."""
        return {
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "batch_size": self.batch_size,
            "parallel_execution": self.parallel_execution,
            "has_retry_limit": self.max_retries is not None,
            "has_timeout": self.timeout_seconds is not None,
            "supports_batching": self.batch_size is not None,
        }

    def is_configured_for_performance(self) -> bool:
        """Check if configured for performance."""
        return (
            self.parallel_execution
            and self.batch_size is not None
            and self.batch_size > 1
        )

    @classmethod
    def create_default(cls) -> ModelNodeExecutionSettings:
        """Create default execution settings."""
        return cls()

    @classmethod
    def create_performance_optimized(
        cls,
        batch_size: int = 10,
        parallel: bool = True,
    ) -> ModelNodeExecutionSettings:
        """Create performance-optimized settings."""
        return cls(
            batch_size=batch_size,
            parallel_execution=parallel,
            max_retries=3,
            timeout_seconds=300,
        )


# Export for use
__all__ = ["ModelNodeExecutionSettings"]
