# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event bus endpoint contract model for delegation runtime configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDelegationEventBusEndpoint(BaseModel):
    """Event bus endpoint configuration for delegation routing."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    provider: str = Field(
        ..., description="Event bus provider identifier (e.g. redpanda, kafka)"
    )
    bootstrap_servers: list[str] = Field(
        ...,
        min_length=1,
        description="Bootstrap server addresses; at least one required",
    )
    topic_policy_ref: str = Field(..., description="Reference to topic policy contract")
    consumer_groups: list[str] = Field(
        default_factory=list,
        description="Consumer group identifiers for this endpoint",
    )
