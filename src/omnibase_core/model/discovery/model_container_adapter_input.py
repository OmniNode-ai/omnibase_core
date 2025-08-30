"""Container Adapter Input model for ONEX Discovery & Integration Event Registry.

This module defines the input model used by the Container Adapter tool
for ONEX Discovery & Integration Event Registry operations.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.discovery.model_event_descriptor import ModelEventDescriptor
from omnibase_core.model.discovery.model_event_discovery_request import (
    ModelEventDiscoveryRequest,
)
from omnibase_core.model.discovery.model_hub_registration_event import (
    ModelHubRegistrationEvent,
)


class ModelContainerAdapterInput(BaseModel):
    """Input model for Container Adapter tool operations."""

    action: str = Field(
        ...,
        description="Action to perform (discover_services, register_service, etc.)",
    )

    # Optional inputs based on action
    discovery_request: ModelEventDiscoveryRequest | None = Field(
        None,
        description="Discovery request for service queries",
    )

    event_descriptor: ModelEventDescriptor | None = Field(
        None,
        description="Event descriptor for registration/updates",
    )

    hub_registration: ModelHubRegistrationEvent | None = Field(
        None,
        description="Hub registration data for Consul",
    )

    service_id: str | None = Field(
        None,
        description="Service ID for status/health operations",
    )

    event_id: str | None = Field(
        None,
        description="Event ID for deregistration operations",
    )

    health_data: dict[str, str] | None = Field(
        None,
        description="Health data for service updates",
    )

    consul_query: dict[str, str] | None = Field(
        None,
        description="Direct Consul query parameters",
    )

    mesh_data: dict[str, str] | None = Field(
        None,
        description="Mesh coordination data (Phase 3)",
    )

    model_config = ConfigDict(extra="forbid")
