"""
Model for agent health metrics.

Health metrics for a single automation agent.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.monitoring.enum_agent_state import EnumAgentState


class ModelAgentHealthMetrics(BaseModel):
    """Health metrics for a single agent."""

    agent_id: str = Field(..., description="Unique agent identifier")
    status: EnumAgentState = Field(..., description="Current agent status")
    uptime_seconds: int = Field(..., ge=0, description="Agent uptime in seconds")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    error_count: int = Field(0, ge=0, description="Total error count")
    success_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Success rate percentage",
    )
    tasks_completed: int = Field(0, ge=0, description="Total tasks completed")
    avg_completion_time: float = Field(
        0.0,
        ge=0,
        description="Average task completion time",
    )
    tokens_consumed: int = Field(0, ge=0, description="Total tokens consumed")
    efficiency_score: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Agent efficiency score",
    )

    memory_usage_mb: float = Field(0.0, ge=0, description="Memory usage in megabytes")
    cpu_utilization: float = Field(
        0.0,
        ge=0,
        le=100,
        description="CPU utilization percentage",
    )
    network_io_bytes_sec: float = Field(
        0.0,
        ge=0,
        description="Network I/O bytes per second",
    )
    queue_depth: int = Field(0, ge=0, description="Current queue depth")

    window_id: str | None = Field(None, description="Current operational window")
    current_task: str | None = Field(None, description="Current task description")

    last_error: str | None = Field(None, description="Last error message")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last metrics update",
    )

    def is_healthy(self) -> bool:
        """Check if agent is in healthy state."""
        return (
            self.status in [EnumAgentState.RUNNING, EnumAgentState.IDLE]
            and self.success_rate >= 85.0
            and self.error_count < 10
        )

    def time_since_heartbeat(self) -> float:
        """Get seconds since last heartbeat."""
        return (datetime.utcnow() - self.last_heartbeat).total_seconds()
