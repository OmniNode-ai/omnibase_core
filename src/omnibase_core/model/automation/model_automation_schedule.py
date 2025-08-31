"""
Model for automation scheduling.

This model defines the complete automation schedule configuration
for managing 24/7 automation schedules for Claude Code agents.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.automation.model_agent_allocation import (
    EnumAgentStatus,
    ModelAgentAllocation,
)
from omnibase_core.model.automation.model_operational_window import (
    ModelOperationalWindow,
)
from omnibase_core.model.automation.model_schedule_statistics import (
    ModelScheduleStatistics,
)


class ModelAutomationSchedule(BaseModel):
    """Complete automation schedule configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    schedule_id: str = Field(..., description="Unique schedule identifier")
    name: str = Field(..., description="Schedule name")
    description: str | None = Field(None, description="Schedule description")

    windows: list[ModelOperationalWindow] = Field(
        ...,
        description="List of operational windows",
    )

    active_agents: list[ModelAgentAllocation] = Field(
        default_factory=list,
        description="Currently active agent allocations",
    )

    daily_quota_limit: int = Field(..., gt=0, description="Total daily token quota")
    emergency_reserve: int = Field(..., gt=0, description="Emergency quota reserve")
    quota_consumed: int = Field(0, ge=0, description="Quota consumed today")

    enabled: bool = Field(True, description="Whether schedule is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    current_window: str | None = Field(
        None,
        description="Currently active window ID",
    )
    next_transition: datetime | None = Field(
        None,
        description="Next window transition time",
    )

    statistics: ModelScheduleStatistics | None = Field(
        default=None,
        description="Schedule performance statistics",
    )

    def get_current_window(self) -> ModelOperationalWindow | None:
        """Get the currently active operational window."""
        if not self.current_window:
            return None

        for window in self.windows:
            if window.window_id == self.current_window:
                return window
        return None

    def get_available_quota(self) -> int:
        """Calculate available quota remaining."""
        return max(
            0,
            self.daily_quota_limit - self.quota_consumed - self.emergency_reserve,
        )

    def can_spawn_agent(self, window_id: str) -> bool:
        """Check if a new agent can be spawned in the specified window."""
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if not window or not window.enabled:
            return False

        active_in_window = sum(
            1
            for agent in self.active_agents
            if agent.window_id == window_id
            and agent.status in [EnumAgentStatus.RUNNING, EnumAgentStatus.IDLE]
        )

        return active_in_window < window.max_agents

    def get_window_metrics(
        self,
        window_id: str,
    ) -> dict[str, str | int | float | bool]:
        """Get performance metrics for a specific window."""
        agents = [a for a in self.active_agents if a.window_id == window_id]

        if not agents:
            return {
                "active_agents": 0,
                "tasks_completed": 0,
                "tokens_consumed": 0,
                "average_efficiency": 0.0,
                "error_rate": 0.0,
            }

        total_tasks = sum(a.tasks_completed for a in agents)
        total_tokens = sum(a.tokens_consumed for a in agents)
        total_errors = sum(a.error_count for a in agents)
        avg_efficiency = (
            sum(a.efficiency_score for a in agents) / len(agents) if agents else 0
        )

        return {
            "active_agents": len(agents),
            "tasks_completed": total_tasks,
            "tokens_consumed": total_tokens,
            "average_efficiency": avg_efficiency,
            "error_rate": (
                (total_errors / total_tasks * 100) if total_tasks > 0 else 0.0
            ),
        }
