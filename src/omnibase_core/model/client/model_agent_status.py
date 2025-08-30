"""
Model for agent status information.

Provides strongly-typed structure for agent status data with proper ONEX compliance.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelAgentStatus(BaseModel):
    """
    Agent status information for remote client operations.

    Replaces Dict[str, Any] usage for ONEX compliance.
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    status: str = Field(
        "unknown", description="Current agent status (active, idle, error, offline)"
    )
    health_score: float = Field(0.0, description="Health score from 0.0 to 1.0")
    last_activity: Optional[datetime] = Field(
        None, description="Timestamp of last activity"
    )
    current_task_id: Optional[str] = Field(
        None, description="ID of currently executing task"
    )
    device_id: Optional[str] = Field(None, description="Device hosting the agent")
    capabilities: Dict[str, bool] = Field(
        default_factory=dict, description="Agent capabilities and their availability"
    )
    resource_usage: Dict[str, float] = Field(
        default_factory=dict, description="Resource usage metrics (cpu, memory, etc.)"
    )
    error_message: Optional[str] = Field(
        None, description="Current error message if any"
    )
