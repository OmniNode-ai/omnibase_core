"""
Model for quota usage tracking.

Complete quota usage tracking across operational windows.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.optimization.model_quota_allocation import \
    ModelQuotaAllocation
from omnibase_core.model.optimization.model_quota_metadata import \
    ModelQuotaMetadata
from omnibase_core.model.optimization.model_usage_snapshot import \
    ModelUsageSnapshot


class ModelQuotaUsage(BaseModel):
    """Complete quota usage tracking."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    quota_id: str = Field(..., description="Unique quota tracking ID")
    daily_limit: int = Field(..., gt=0, description="Daily token limit")
    daily_budget: float = Field(..., gt=0, description="Daily budget in USD")

    total_consumed: int = Field(0, ge=0, description="Total tokens consumed today")
    total_cost: float = Field(0.0, ge=0, description="Total cost today")

    window_allocations: List[ModelQuotaAllocation] = Field(
        default_factory=list, description="Per-window allocations"
    )

    emergency_reserve: int = Field(..., gt=0, description="Emergency token reserve")
    emergency_reserve_used: int = Field(0, ge=0, description="Emergency tokens used")

    reset_time: datetime = Field(
        default_factory=datetime.utcnow, description="Daily reset time"
    )
    last_optimization: Optional[datetime] = Field(
        None, description="Last optimization run"
    )

    snapshots: List[ModelUsageSnapshot] = Field(
        default_factory=list,
        max_length=1440,  # Keep last 24 hours of minute-level snapshots
        description="Recent usage snapshots",
    )

    alerts_triggered: List[str] = Field(
        default_factory=list, description="Alerts triggered today"
    )

    metadata: Optional[ModelQuotaMetadata] = Field(
        default_factory=ModelQuotaMetadata, description="Additional usage data"
    )

    def get_utilization(self) -> float:
        """Get current quota utilization percentage."""
        return (self.total_consumed / self.daily_limit) * 100

    def get_cost_utilization(self) -> float:
        """Get current budget utilization percentage."""
        return (self.total_cost / self.daily_budget) * 100

    def get_remaining_tokens(self) -> int:
        """Get total remaining tokens including emergency reserve."""
        base_remaining = self.daily_limit - self.total_consumed
        reserve_remaining = self.emergency_reserve - self.emergency_reserve_used
        return base_remaining + reserve_remaining

    def is_quota_exhausted(self) -> bool:
        """Check if quota is exhausted."""
        return self.total_consumed >= self.daily_limit

    def is_budget_exhausted(self) -> bool:
        """Check if budget is exhausted."""
        return self.total_cost >= self.daily_budget

    def get_window_allocation(self, window_id: str) -> Optional[ModelQuotaAllocation]:
        """Get allocation for specific window."""
        for allocation in self.window_allocations:
            if allocation.window_id == window_id:
                return allocation
        return None
