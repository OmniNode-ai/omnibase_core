"""
Model for quota allocation.

Quota allocation for a specific operational window.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.optimization.model_allocation_metadata import (
    ModelAllocationMetadata,
)


class ModelQuotaAllocation(BaseModel):
    """Quota allocation for a specific window."""

    window_id: str = Field(..., description="Operational window ID")
    allocated_tokens: int = Field(..., gt=0, description="Tokens allocated to window")
    consumed_tokens: int = Field(0, ge=0, description="Tokens consumed so far")
    successful_tasks: int = Field(0, ge=0, description="Successfully completed tasks")
    failed_tasks: int = Field(0, ge=0, description="Failed tasks")
    priority: str = Field(..., description="Window priority level")

    metadata: ModelAllocationMetadata | None = Field(
        default_factory=ModelAllocationMetadata,
        description="Additional allocation data",
    )

    def calculate_efficiency(self) -> float:
        """Calculate efficiency score for this allocation."""
        if self.consumed_tokens == 0:
            return 0.0

        total_tasks = self.successful_tasks + self.failed_tasks
        if total_tasks == 0:
            return 0.0

        success_rate = self.successful_tasks / total_tasks
        utilization = min(1.0, self.consumed_tokens / self.allocated_tokens)

        # Efficiency is combination of success rate and utilization
        return success_rate * 0.7 + utilization * 0.3

    def get_remaining_tokens(self) -> int:
        """Get remaining tokens in allocation."""
        return max(0, self.allocated_tokens - self.consumed_tokens)

    def can_accept_task(self, estimated_tokens: int) -> bool:
        """Check if allocation can accept a task."""
        return self.get_remaining_tokens() >= estimated_tokens
