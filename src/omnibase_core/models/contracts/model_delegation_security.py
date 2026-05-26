# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Security contract model for delegation runtime configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_delegation_secret_ref import (
    ModelDelegationSecretRef,
)


class ModelDelegationSecurity(BaseModel):
    """Security configuration: allowlists and shared secret reference."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    broker_allowlist_ref: str = Field(
        ...,
        description="Ref to broker allowlist configuration",
    )
    endpoint_cidr_allowlist_ref: str = Field(
        ...,
        description="Ref to CIDR allowlist for endpoint access control",
    )
    shared_secret_ref: ModelDelegationSecretRef = Field(
        ...,
        description="Shared secret reference for service-to-service auth",
    )
