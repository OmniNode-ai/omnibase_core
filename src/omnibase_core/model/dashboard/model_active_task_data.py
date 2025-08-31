"""
Model for active task data in the agent orchestration dashboard.

This model represents the structure of active tasks being tracked
by the multi-agent coordination system.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.debug.model_agent_debug_entry import ModelDebugContext
from omnibase_core.model.work.model_work_ticket import ModelWorkTicket


class ModelActiveTaskData(BaseModel):
    """Model for active task data structure."""

    ticket: ModelWorkTicket | None = Field(
        default=None,
        description="Work ticket associated with this task",
    )
    debug_context: ModelDebugContext | None = Field(
        default=None,
        description="Debug intelligence context for the task",
    )
    trace_id: str = Field(description="Unique trace identifier for the task")
    status: str = Field(default="pending", description="Current task status")
    agent_id: str | None = Field(default=None, description="ID of assigned agent")
    execution_log: list[str] = Field(
        default_factory=list,
        description="Log of execution steps and events",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Task creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )
