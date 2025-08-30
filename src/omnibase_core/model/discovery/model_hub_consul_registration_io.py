"""Input/Output models for Hub Consul Registration tool.

This module defines the input and output models used by the Hub Consul Registration tool
for automatic hub self-registration in Consul service discovery.
"""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.discovery.model_hub_registration_event import \
    ModelHubRegistrationEvent


class ModelHubConsulRegistrationInput(BaseModel):
    """Input model for Hub Consul Registration tool operations."""

    action: str = Field(
        ...,
        description="Action to perform (auto_register, register_hub, deregister_hub, etc.)",
    )

    # Optional inputs based on action
    hub_domain: Optional[str] = Field(None, description="Hub domain for registration")

    hub_port: Optional[int] = Field(
        None, description="Hub port for service registration"
    )

    registration_event: Optional[ModelHubRegistrationEvent] = Field(
        None, description="Hub registration event for manual registration"
    )

    hub_id: Optional[str] = Field(
        None, description="Hub ID for status/deregistration operations"
    )

    model_config = ConfigDict(extra="forbid")


class ModelHubConsulRegistrationOutput(BaseModel):
    """Output model for Hub Consul Registration tool operations."""

    action_result: str = Field(..., description="Result of the requested action")

    # Optional outputs based on action
    registration_event: Optional[ModelHubRegistrationEvent] = Field(
        None, description="Hub registration event that was created/processed"
    )

    registration_success: Optional[bool] = Field(
        None, description="Registration operation success"
    )

    deregistration_success: Optional[bool] = Field(
        None, description="Deregistration operation success"
    )

    hub_status: Optional[Dict[str, str]] = Field(
        None, description="Hub registration status information"
    )

    registered_hubs: Optional[Dict[str, Dict[str, str]]] = Field(
        None, description="List of all registered hubs with status"
    )

    # Always present metadata
    registration_tool_id: str = Field(
        ..., description="Hub registration tool instance ID"
    )

    operation_timestamp: str = Field(..., description="Operation timestamp")

    # Error handling
    error_details: Optional[str] = Field(
        None, description="Error details if operation failed"
    )

    operation_successful: bool = Field(
        True, description="Whether operation was successful"
    )

    model_config = ConfigDict(extra="forbid")
