# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hub Registration Event model for ONEX Discovery & Integration Event Registry.

This module defines the Hub self-registration event for service registry.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHubRegistrationEvent(BaseModel):
    """Hub self-registration event for service registry."""

    # Hub Identity
    hub_id: UUID = Field(default=..., description="Unique hub identifier")
    hub_name: str = Field(default=..., description="Hub name")
    hub_domain: str = Field(default=..., description="Hub domain")
    hub_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Hub version",
    )

    # Registration Details
    registration_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Registration timestamp",
    )
    registration_required: bool = Field(
        default=True,
        description="Whether registration is required",
    )
    auto_deregister_on_shutdown: bool = Field(
        default=True,
        description="Auto-deregister on shutdown",
    )

    # Event Registry Integration
    event_registry_enabled: bool = Field(
        default=True,
        description="Whether Event Registry is enabled",
    )
    container_adapter_coordination: bool = Field(
        default=True,
        description="Container Adapter coordination enabled",
    )

    model_config = ConfigDict(extra="forbid")
