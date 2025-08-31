"""
Model for agent discovery request events.

Defines request to discover available agents in the system.
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent


class ModelAgentDiscoveryRequest(BaseModel):
    """Request to discover available agents in the system."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    requester_id: str = Field(..., description="ID of the requester")

    @classmethod
    def create_event(
        cls,
        node_id: str,
        request: "ModelAgentDiscoveryRequest",
    ) -> ModelOnexEvent:
        """Create ONEX event for discovery request."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="discovery_request",
            node_id=node_id,
            data={"discovery_request": request.model_dump()},
        )

    def wrap_in_envelope(self, source_node_id: str) -> ModelEventEnvelope:
        """Wrap discovery request in event envelope for broadcast."""
        event = self.create_event(source_node_id, self)

        # Broadcast to all agents
        return ModelEventEnvelope.create_broadcast(
            payload=event,
            source_node_id=source_node_id,
        )

    # Discovery filters
    required_capabilities: list[EnumAgentCapability] | None = Field(None)
    preferred_roles: list[str] | None = Field(None)
    preferred_locations: list[str] | None = Field(None)
    minimum_health_status: str | None = Field("healthy")

    # Response preferences
    include_offline_agents: bool = Field(False)
    include_busy_agents: bool = Field(True)
    max_results: int = Field(100, ge=1, le=1000)

    timestamp: datetime = Field(default_factory=datetime.now)
