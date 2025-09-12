"""
Model for agent task result events.

Defines the result of a completed agent task.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.events.model_agent_result_data import ModelAgentTaskResultData


class ModelAgentTaskResult(BaseModel):
    """Result of a completed agent task."""

    task_id: str = Field(..., description="Task ID")
    agent_id: str = Field(..., description="Agent ID that processed the task")
    correlation_id: str = Field(..., description="Original correlation ID")

    @classmethod
    def create_event(
        cls,
        node_id: str,
        result: "ModelAgentTaskResult",
        correlation_id: UUID | None = None,
    ) -> ModelOnexEvent:
        """Create ONEX event for task result."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="task_result",
            node_id=node_id,
            correlation_id=correlation_id or UUID(result.correlation_id),
            data={"task_result": result.model_dump()},
        )

    def wrap_in_envelope(
        self,
        source_node_id: str,
        destination: str,
    ) -> ModelEventEnvelope:
        """Wrap task result in event envelope for routing back to requester."""
        event = self.create_event(source_node_id, self)

        return ModelEventEnvelope.create_direct(
            payload=event,
            destination=destination,
            source_node_id=source_node_id,
            correlation_id=self.correlation_id,
        )

    # Result data
    success: bool = Field(..., description="Whether task completed successfully")
    result_text: str | None = Field(None, description="Text result from agent")
    result_data: ModelAgentTaskResultData = Field(
        default_factory=ModelAgentTaskResultData,
        description="Structured result data",
    )
    error_message: str | None = Field(None, description="Error message if failed")

    # Execution metadata
    execution_time_seconds: float = Field(..., description="Total execution time")
    tokens_used: int = Field(..., description="Total tokens consumed")
    model_used: str = Field(..., description="Actual model used")
    provider_used: str = Field(..., description="Actual provider used")

    # Quality metrics
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    quality_checks_passed: list[str] | None = Field(None)

    # Timestamps
    started_at: datetime = Field(...)
    completed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "task_id": "task_123",
                "agent_id": "code_reviewer_a3f2b8c1",
                "success": True,
                "result_text": "Code review completed. Found 3 issues...",
                "execution_time_seconds": 12.5,
                "tokens_used": 1250,
                "model_used": "codellama:13b-instruct",
                "provider_used": "ollama",
            },
        }
