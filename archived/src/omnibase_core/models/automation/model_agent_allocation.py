"""
Model for agent allocation.

Tracks agent allocation within an operational window.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.models.automation.model_agent_metadata import ModelAgentMetadata


class EnumAgentStatus(str, Enum):
    """Status of an automation agent."""

    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class ModelAgentAllocation(BaseModel):
    """Tracks agent allocation within a window."""

    agent_id: str = Field(..., description="Unique agent identifier")
    window_id: str = Field(..., description="Assigned window ID")
    status: EnumAgentStatus = Field(..., description="Current agent status")
    current_task: str | None = Field(None, description="Current task being executed")
    tasks_completed: int = Field(0, ge=0, description="Number of tasks completed")
    tokens_consumed: int = Field(0, ge=0, description="Tokens consumed by this agent")
    efficiency_score: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Agent efficiency score",
    )
    last_heartbeat: datetime = Field(..., description="Last health check timestamp")
    error_count: int = Field(0, ge=0, description="Number of errors encountered")

    metadata: ModelAgentMetadata | None = Field(
        default=None,
        description="Additional agent metrics",
    )
