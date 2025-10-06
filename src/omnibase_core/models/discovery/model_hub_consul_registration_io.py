from typing import Optional

from pydantic import Field

"""Input/Output models for Hub Consul Registration tool.

This module defines the input and output models used by the Hub Consul Registration tool
for automatic hub self-registration in Consul service discovery.
"""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_hub_registration_event import (
    ModelHubRegistrationEvent,
)

from .model_hubconsulregistrationoutput import ModelHubConsulRegistrationOutput


class ModelHubConsulRegistrationInput(BaseModel):
    """Input model for Hub Consul Registration tool operations."""

    action: str = Field(
        ...,
        description="Action to perform (auto_register, register_hub, deregister_hub, etc.)",
    )

    # Optional inputs based on action
    hub_domain: str | None = Field(
        default=None, description="Hub domain for registration"
    )

    hub_port: int | None = Field(
        default=None,
        description="Hub port for service registration",
    )

    registration_event: ModelHubRegistrationEvent | None = Field(
        default=None,
        description="Hub registration event for manual registration",
    )

    hub_id: str | None = Field(
        default=None,
        description="Hub ID for status/deregistration operations",
    )

    model_config = ConfigDict(extra="forbid")
