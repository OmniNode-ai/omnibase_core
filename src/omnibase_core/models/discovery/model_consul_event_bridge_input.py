"""Consul Event Bridge Input model for ONEX Discovery & Integration Event Registry.

This module defines the input model for Consul Event Bridge operations.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import ModelEventDescriptor


class ModelConsulEventBridgeInput(BaseModel):
    """Input model for Consul Event Bridge operations."""

    bridge_action: str = Field(default=..., description="Bridge action to perform")

    event_descriptor: ModelEventDescriptor | None = Field(
        default=None,
        description="ONEX event to bridge to Consul",
    )

    consul_service_data: dict[str, str] | None = Field(
        default=None,
        description="Consul service data to bridge to ONEX event",
    )

    sync_required: bool = Field(
        default=False,
        description="Whether to perform state synchronization",
    )

    monitoring_callback: str | None = Field(
        default=None,
        description="Callback function name for monitoring",
    )

    model_config = ConfigDict(extra="forbid")
