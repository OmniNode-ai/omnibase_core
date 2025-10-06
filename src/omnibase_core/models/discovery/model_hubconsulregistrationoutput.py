from typing import Dict, List

from pydantic import BaseModel, Field


class ModelHubConsulRegistrationOutput(BaseModel):
    """Output model for Hub Consul Registration tool operations."""

    action_result: str = Field(..., description="Result of the requested action")

    # Optional outputs based on action
    registration_event: ModelHubRegistrationEvent | None = Field(
        None,
        description="Hub registration event that was created/processed",
    )

    registration_success: bool | None = Field(
        None,
        description="Registration operation success",
    )

    deregistration_success: bool | None = Field(
        None,
        description="Deregistration operation success",
    )

    hub_status: dict[str, str] | None = Field(
        None,
        description="Hub registration status information",
    )

    registered_hubs: dict[str, dict[str, str]] | None = Field(
        None,
        description="List of all registered hubs with status",
    )

    # Always present metadata
    registration_tool_id: str = Field(
        ...,
        description="Hub registration tool instance ID",
    )

    operation_timestamp: str = Field(..., description="Operation timestamp")

    # Error handling
    error_details: str | None = Field(
        None,
        description="Error details if operation failed",
    )

    operation_successful: bool = Field(
        True,
        description="Whether operation was successful",
    )

    model_config = ConfigDict(extra="forbid")
