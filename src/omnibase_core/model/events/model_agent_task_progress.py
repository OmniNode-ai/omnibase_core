"""
Model for agent task progress events.

Defines progress updates for an ongoing task.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_onex_event import ModelOnexEvent


class ModelAgentTaskProgress(BaseModel):
    """Progress update for an ongoing task."""

    task_id: str = Field(..., description="Task ID")
    agent_id: str = Field(..., description="Agent ID processing the task")

    # Progress information
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    current_step: str | None = Field(None, description="Current processing step")
    steps_completed: int = Field(0, ge=0)
    total_steps: int | None = Field(None)

    # Resource usage
    tokens_used: int = Field(0, ge=0)
    estimated_tokens_remaining: int | None = Field(None)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def create_event(
        cls,
        node_id: str,
        progress: "ModelAgentTaskProgress",
        correlation_id: UUID | None = None,
    ) -> ModelOnexEvent:
        """Create ONEX event for task progress."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="task_progress",
            node_id=node_id,
            correlation_id=correlation_id,
            data={"task_progress": progress.model_dump()},
        )
