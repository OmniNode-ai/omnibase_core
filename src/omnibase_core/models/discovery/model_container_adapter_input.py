from uuid import UUID

from pydantic import Field

"Container Adapter Input model for ONEX Discovery & Integration Event Registry.\n\nThis module defines the input model used by the Container Adapter tool\nfor ONEX Discovery & Integration Event Registry operations.\n"

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.discovery.model_event_descriptor import ModelEventDescriptor
from omnibase_core.models.discovery.model_event_discovery_request import (
    ModelEventDiscoveryRequest,
)
from omnibase_core.models.discovery.model_hub_registration_event import (
    ModelHubRegistrationEvent,
)


class ModelContainerAdapterInput(BaseModel):
    """Input model for Container Adapter tool operations."""

    action: str = Field(
        default=...,
        description="Action to perform (discover_services, register_service, etc.)",
    )
    discovery_request: ModelEventDiscoveryRequest | None = Field(
        default=None, description="Discovery request for service queries"
    )
    event_descriptor: ModelEventDescriptor | None = Field(
        default=None, description="Event descriptor for registration/updates"
    )
    hub_registration: ModelHubRegistrationEvent | None = Field(
        default=None, description="Hub registration data for Consul"
    )
    service_id: UUID | None = Field(
        default=None, description="Service ID for status/health operations"
    )
    event_id: UUID | None = Field(
        default=None, description="Event ID for deregistration operations"
    )
    health_data: dict[str, str] | None = Field(
        default=None, description="Health data for service updates"
    )
    consul_query: dict[str, str] | None = Field(
        default=None, description="Direct Consul query parameters"
    )
    mesh_data: dict[str, str] | None = Field(
        default=None, description="Mesh coordination data (Phase 3)"
    )
    model_config = ConfigDict(extra="forbid")
