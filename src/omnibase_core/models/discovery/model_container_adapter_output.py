"""Container Adapter Output model for ONEX Discovery & Integration Event Registry.

This module defines the output model used by the Container Adapter tool
for ONEX Discovery & Integration Event Registry operations.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import (
    EnumDiscoveryPhase,
    EnumServiceStatus,
)
from omnibase_core.models.discovery.model_event_discovery_response import (
    ModelEventDiscoveryResponse,
)


class ModelContainerAdapterOutput(BaseModel):
    """Output model for Container Adapter tool operations."""

    action_result: str = Field(
        default=..., description="Result of the requested action"
    )

    # Optional outputs based on action
    discovery_response: ModelEventDiscoveryResponse | None = Field(
        default=None,
        description="Discovery query results",
    )

    service_status: EnumServiceStatus | None = Field(
        default=None,
        description="Service status information",
    )

    registration_success: bool | None = Field(
        default=None,
        description="Registration operation success",
    )

    deregistration_success: bool | None = Field(
        default=None,
        description="Deregistration operation success",
    )

    health_update_success: bool | None = Field(
        default=None,
        description="Health update operation success",
    )

    consul_services: list[dict[str, str]] | None = Field(
        default=None,
        description="Direct Consul query results",
    )

    # Always present metadata
    discovery_phase: EnumDiscoveryPhase = Field(
        default=...,
        description="Current discovery implementation phase",
    )

    container_adapter_id: UUID = Field(
        default=..., description="Container Adapter instance ID"
    )

    operation_timestamp: str = Field(default=..., description="Operation timestamp")

    # Error handling
    error_details: str | None = Field(
        default=None,
        description="Error details if operation failed",
    )

    operation_successful: bool = Field(
        default=True,
        description="Whether operation was successful",
    )

    model_config = ConfigDict(extra="forbid")
