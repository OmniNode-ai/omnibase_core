"""
Model for agent task request events.

Defines strongly-typed request to execute a task on a distributed agent.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_llm_provider import EnumLLMProvider
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent


class ModelAgentTaskRequest(BaseModel):
    """Request to execute a task on a distributed agent."""

    # Task identification
    task_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique task identifier",
    )
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Correlation ID for tracking",
    )

    @classmethod
    def create_event(
        cls,
        node_id: str,
        task_request: "ModelAgentTaskRequest",
        correlation_id: UUID | None = None,
    ) -> ModelOnexEvent:
        """Create ONEX event for task request."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="task_request",
            node_id=node_id,
            correlation_id=correlation_id or UUID(task_request.correlation_id),
            data={"task_request": task_request.model_dump()},
        )

    def wrap_in_envelope(
        self,
        source_node_id: str,
        destination: str | None = None,
    ) -> ModelEventEnvelope:
        """Wrap task request in event envelope for routing."""
        event = self.create_event(source_node_id, self)

        if destination:
            return ModelEventEnvelope.create_direct(
                payload=event,
                destination=destination,
                source_node_id=source_node_id,
            )
        # Anycast to any available agent executor service
        return ModelEventEnvelope.create_anycast(
            payload=event,
            service_pattern="service://agent-executor",
            source_node_id=source_node_id,
        )

    # Task details
    task_type: str = Field(
        ...,
        description="Type of task (e.g., 'code_review', 'documentation')",
    )
    prompt: str = Field(..., description="Task prompt/instructions")
    system_prompt: str | None = Field(None, description="System prompt for context")

    # Routing preferences
    preferred_agent_role: str | None = Field(
        None,
        description="Preferred agent role",
    )
    required_capabilities: list[EnumAgentCapability] = Field(default_factory=list)
    preferred_providers: list[EnumLLMProvider] = Field(default_factory=list)
    preferred_location: str | None = Field(None, description="home_lab, remote, any")

    # Task metadata
    priority: int = Field(1, ge=1, le=10, description="Task priority (1-10)")
    timeout_seconds: int = Field(300, description="Task timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")

    # Security and tracking
    requester_id: str = Field(..., description="ID of the requester")
    requester_location: str | None = Field(None, description="Location of requester")
    auth_token: str | None = Field(
        None,
        description="Authentication token for secure access",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = Field(None, description="Task expiration time")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "task_type": "code_review",
                "prompt": "Review this Python function for security vulnerabilities",
                "preferred_agent_role": "code_reviewer",
                "required_capabilities": ["code_review", "security_analysis"],
                "preferred_location": "home_lab",
                "priority": 5,
                "requester_id": "remote_user_123",
            },
        }
