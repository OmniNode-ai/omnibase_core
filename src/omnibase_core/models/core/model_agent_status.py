from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_agent_status_type import EnumAgentStatusType
from omnibase_core.models.core.model_agent_activity import ModelAgentActivity
from omnibase_core.models.core.model_resource_metrics import ModelResourceMetrics

__all__ = [
    "EnumAgentStatusType",
    "ModelAgentStatus",
]


class ModelAgentStatus(BaseModel):
    """Complete agent status information."""

    agent_id: UUID = Field(description="Unique identifier of the agent")
    status: EnumAgentStatusType = Field(description="Current status of the agent")
    activity: ModelAgentActivity = Field(description="Current activity information")
    resource_usage: ModelResourceMetrics = Field(description="Resource usage metrics")
    health_score: float = Field(description="Health score from 0.0 to 1.0")
    error_level_count: int = Field(
        default=0, description="Number of errors since last reset"
    )
    last_error: str | None = Field(
        default=None, description="Description of last error"
    )
    uptime_seconds: int = Field(description="Agent uptime in seconds")
    tasks_completed: int = Field(
        default=0, description="Number of tasks completed since start"
    )
    tasks_failed: int = Field(
        default=0, description="Number of tasks failed since start"
    )
    started_at: datetime = Field(description="Agent start timestamp")
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Status last update timestamp"
    )
