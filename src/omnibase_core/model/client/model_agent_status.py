"""
Model for agent status information.

Provides strongly-typed structure for agent status data with proper ONEX compliance.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelAgentStatus(BaseModel):
    """
    Agent status information for remote client operations.

    Replaces Dict[str, Any] usage for ONEX compliance.
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    status: str = Field(
        "unknown",
        description="Current agent status (active, idle, error, offline)",
    )
    health_score: float = Field(0.0, description="Health score from 0.0 to 1.0")
    last_activity: datetime | None = Field(
        None,
        description="Timestamp of last activity",
    )
    current_task_id: str | None = Field(
        None,
        description="ID of currently executing task",
    )
    device_id: str | None = Field(None, description="Device hosting the agent")
    capabilities: dict[str, bool] = Field(
        default_factory=dict,
        description="Agent capabilities and their availability",
    )
    resource_usage: dict[str, float] = Field(
        default_factory=dict,
        description="Resource usage metrics (cpu, memory, etc.)",
    )
    error_message: str | None = Field(
        None,
        description="Current error message if any",
    )
