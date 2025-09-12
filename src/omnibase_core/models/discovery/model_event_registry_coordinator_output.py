"""Event Registry Coordinator Output model for ONEX Discovery & Integration Event Registry.

This module defines the output model for Event Registry Coordinator operations.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import ServiceStatusEnum


class ModelEventRegistryCoordinatorOutput(BaseModel):
    """Output model for Event Registry Coordinator operations."""

    coordinator_result: str = Field(..., description="Coordinator operation result")

    phase_initialization_success: bool | None = Field(
        None,
        description="Phase initialization success",
    )

    active_adapters: list[str] | None = Field(
        None,
        description="List of active Container Adapter IDs",
    )

    routing_success: bool | None = Field(None, description="Event routing success")

    coordination_success: bool | None = Field(
        None,
        description="Cross-adapter coordination success",
    )

    adapter_health_status: dict[str, ServiceStatusEnum] | None = Field(
        None,
        description="Health status of Container Adapters",
    )

    operation_timestamp: str = Field(..., description="Operation timestamp")

    error_details: str | None = Field(
        None,
        description="Error details if operation failed",
    )

    operation_successful: bool = Field(
        True,
        description="Whether operation was successful",
    )

    model_config = ConfigDict(extra="forbid")
