"""
Model for agent task assignment events.

Defines assignment of a task to a specific agent.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_llm_provider import EnumLLMProvider
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class ModelAgentTaskAssignment(BaseModel):
    """Assignment of a task to a specific agent."""

    task_id: str = Field(..., description="Task ID being assigned")
    agent_id: str = Field(..., description="Agent ID receiving the task")
    agent_role: str = Field(..., description="Role of the assigned agent")
    agent_location: str = Field(..., description="Location of the agent (device)")
    provider: EnumLLMProvider = Field(..., description="LLM provider being used")
    model_id: str = Field(..., description="Model being used")

    # Assignment metadata
    assigned_at: datetime = Field(default_factory=datetime.now)
    estimated_completion_seconds: int | None = Field(None)
    queue_position: int | None = Field(
        None,
        description="Position in queue if queued",
    )

    # Status
    status: str = Field("assigned", description="assigned, queued, rejected")
    rejection_reason: str | None = Field(None)

    @classmethod
    def create_event(
        cls,
        node_id: str,
        assignment: "ModelAgentTaskAssignment",
        correlation_id: UUID | None = None,
    ) -> ModelOnexEvent:
        """Create ONEX event for task assignment."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="task_assignment",
            node_id=node_id,
            correlation_id=correlation_id,
            data={"task_assignment": assignment.model_dump()},
        )
