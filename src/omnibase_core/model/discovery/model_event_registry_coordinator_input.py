"""Event Registry Coordinator Input model for ONEX Discovery & Integration Event Registry.

This module defines the input model for Event Registry Coordinator operations.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.discovery.model_event_descriptor import (
    DiscoveryPhaseEnum,
    ModelEventDescriptor,
)


class ModelEventRegistryCoordinatorInput(BaseModel):
    """Input model for Event Registry Coordinator operations."""

    coordinator_action: str = Field(..., description="Coordinator action to perform")

    discovery_phase: DiscoveryPhaseEnum | None = Field(
        None,
        description="Discovery phase to initialize",
    )

    event_descriptor: ModelEventDescriptor | None = Field(
        None,
        description="Event for routing/coordination",
    )

    adapter_id: str | None = Field(None, description="Target Container Adapter ID")

    cross_adapter_coordination: bool = Field(
        False,
        description="Whether to coordinate across multiple adapters",
    )

    model_config = ConfigDict(extra="forbid")
