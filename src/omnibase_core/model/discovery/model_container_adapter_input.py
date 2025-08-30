"""Container Adapter Input model for ONEX Discovery & Integration Event Registry.

This module defines the input model used by the Container Adapter tool
for ONEX Discovery & Integration Event Registry operations.
"""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.discovery.model_event_descriptor import \
    ModelEventDescriptor
from omnibase_core.model.discovery.model_event_discovery_request import \
    ModelEventDiscoveryRequest
from omnibase_core.model.discovery.model_hub_registration_event import \
    ModelHubRegistrationEvent


class ModelContainerAdapterInput(BaseModel):
    """Input model for Container Adapter tool operations."""

    action: str = Field(
        ..., description="Action to perform (discover_services, register_service, etc.)"
    )

    # Optional inputs based on action
    discovery_request: Optional[ModelEventDiscoveryRequest] = Field(
        None, description="Discovery request for service queries"
    )

    event_descriptor: Optional[ModelEventDescriptor] = Field(
        None, description="Event descriptor for registration/updates"
    )

    hub_registration: Optional[ModelHubRegistrationEvent] = Field(
        None, description="Hub registration data for Consul"
    )

    service_id: Optional[str] = Field(
        None, description="Service ID for status/health operations"
    )

    event_id: Optional[str] = Field(
        None, description="Event ID for deregistration operations"
    )

    health_data: Optional[Dict[str, str]] = Field(
        None, description="Health data for service updates"
    )

    consul_query: Optional[Dict[str, str]] = Field(
        None, description="Direct Consul query parameters"
    )

    mesh_data: Optional[Dict[str, str]] = Field(
        None, description="Mesh coordination data (Phase 3)"
    )

    model_config = ConfigDict(extra="forbid")
