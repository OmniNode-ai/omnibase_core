"""
Model for agent discovery response events.

Defines response with discovered agents.
"""

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.events.model_agent_discovery_info import \
    ModelAgentDiscoveryInfo


class ModelAgentDiscoveryResponse(BaseModel):
    """Response with discovered agents."""

    request_id: str = Field(..., description="Original request ID")
    discovered_agents: List[ModelAgentDiscoveryInfo] = Field(
        default_factory=list, description="List of discovered agents"
    )
    total_agents: int = Field(0, ge=0)
    online_agents: int = Field(0, ge=0)
    available_agents: int = Field(0, ge=0)

    # Summary by location
    agents_by_location: Dict[str, int] = Field(default_factory=dict)

    # Summary by role
    agents_by_role: Dict[str, int] = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=datetime.now)

    @classmethod
    def create_event(
        cls, node_id: str, response: "ModelAgentDiscoveryResponse"
    ) -> ModelOnexEvent:
        """Create ONEX event for discovery response."""
        return ModelOnexEvent.create_plugin_event(
            plugin_name="agent",
            action="discovery_response",
            node_id=node_id,
            data={"discovery_response": response.model_dump()},
        )

    def wrap_in_envelope(
        self, source_node_id: str, destination: str
    ) -> ModelEventEnvelope:
        """Wrap discovery response in event envelope for routing."""
        event = self.create_event(source_node_id, self)

        return ModelEventEnvelope.create_direct(
            payload=event, destination=destination, source_node_id=source_node_id
        )
