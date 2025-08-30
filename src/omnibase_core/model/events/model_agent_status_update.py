"""
Model for agent status update events.

Defines status updates from an agent in the distributed system.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent


class ModelAgentStatusUpdate(BaseModel):
    """Status update from an agent in the distributed system."""

    agent_id: str = Field(..., description="Agent ID")
    agent_role: str = Field(..., description="Agent role")
    location: str = Field(..., description="Agent location (device)")

    @classmethod
    def create_event(
        cls,
        node_id: str,
        status: "ModelAgentStatusUpdate",
    ) -> ModelOnexEvent:
        """Create ONEX event for agent status update."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="status_update",
            node_id=node_id,
            data={"agent_status": status.model_dump()},
        )

    def wrap_in_envelope(self, source_node_id: str) -> ModelEventEnvelope:
        """Wrap status update in event envelope for broadcast."""
        event = self.create_event(source_node_id, self)

        # Broadcast status to all interested parties
        return ModelEventEnvelope.create_broadcast(
            payload=event,
            source_node_id=source_node_id,
        )

    # Current status
    status: str = Field(..., description="idle, busy, error, offline")
    current_task_id: str | None = Field(None)
    queue_depth: int = Field(0, ge=0, description="Number of queued tasks")

    # Health metrics
    health_status: str = Field("healthy", description="healthy, degraded, unhealthy")
    cpu_usage_percent: float = Field(0.0, ge=0.0, le=100.0)
    memory_usage_mb: float = Field(0.0, ge=0.0)

    # Capabilities
    available_capabilities: list[EnumAgentCapability] = Field(default_factory=list)
    model_info: dict[str, str] = Field(
        default_factory=dict,
        description="Model information as string key-value pairs",
    )

    # Timestamps
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    uptime_seconds: int = Field(0, ge=0)
