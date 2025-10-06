from pydantic import Field

"""Event Registry Coordinator Input model for ONEX Discovery & Integration Event Registry.

This module defines the input model for Event Registry Coordinator operations.
"""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import (
    EnumDiscoveryPhase,
    ModelEventDescriptor,
)


class ModelEventRegistryCoordinatorInput(BaseModel):
    """Input model for Event Registry Coordinator operations."""

    coordinator_action: str = Field(
        default=..., description="Coordinator action to perform"
    )

    discovery_phase: EnumDiscoveryPhase | None = Field(
        default=None,
        description="Discovery phase to initialize",
    )

    event_descriptor: ModelEventDescriptor | None = Field(
        default=None,
        description="Event for routing/coordination",
    )

    adapter_id: str | None = Field(
        default=None, description="Target Container Adapter ID"
    )

    cross_adapter_coordination: bool = Field(
        default=False,
        description="Whether to coordinate across multiple adapters",
    )

    model_config = ConfigDict(extra="forbid")
