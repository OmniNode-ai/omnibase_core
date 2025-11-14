from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_hub_registration_event import (
    ModelHubRegistrationEvent,
)


class ModelHubConsulRegistrationOutput(BaseModel):
    """Output model for Hub Consul Registration tool operations."""

    action_result: str = Field(
        default=..., description="Result of the requested action"
    )

    # Optional outputs based on action
    registration_event: ModelHubRegistrationEvent | None = Field(
        default=None,
        description="Hub registration event that was created/processed",
    )

    registration_success: bool | None = Field(
        default=None,
        description="Registration operation success",
    )

    deregistration_success: bool | None = Field(
        default=None,
        description="Deregistration operation success",
    )

    hub_status: dict[str, str] | None = Field(
        default=None,
        description="Hub registration status information",
    )

    registered_hubs: dict[str, dict[str, str]] | None = Field(
        default=None,
        description="List of all registered hubs with status",
    )

    # Always present metadata
    registration_tool_id: UUID = Field(
        default=...,
        description="Hub registration tool instance ID",
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
