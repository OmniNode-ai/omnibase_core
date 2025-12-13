"""Event Registry Coordinator Output model for ONEX Discovery & Integration Event Registry.

This module defines the output model for Event Registry Coordinator operations.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_service_status import EnumServiceStatus


class ModelEventRegistryCoordinatorOutput(BaseModel):
    """Output model for Event Registry Coordinator operations."""

    coordinator_result: str = Field(
        default=..., description="Coordinator operation result"
    )

    phase_initialization_success: bool | None = Field(
        default=None,
        description="Phase initialization success",
    )

    active_adapters: list[str] | None = Field(
        default=None,
        description="List of active Container Adapter IDs",
    )

    routing_success: bool | None = Field(
        default=None, description="Event routing success"
    )

    coordination_success: bool | None = Field(
        default=None,
        description="Cross-adapter coordination success",
    )

    adapter_health_status: dict[str, EnumServiceStatus] | None = Field(
        default=None,
        description="Health status of Container Adapters",
    )

    operation_timestamp: str = Field(default=..., description="Operation timestamp")

    error_details: str | None = Field(
        default=None,
        description="Error details if operation failed",
    )

    operation_successful: bool = Field(
        default=True,
        description="Whether operation was successful",
    )

    model_config = ConfigDict(extra="forbid")
