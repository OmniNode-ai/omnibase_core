# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Projection API contract model for delegation runtime configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDelegationProjectionApi(BaseModel):
    """Projection API connection configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    base_url_ref: str = Field(
        ...,
        description="Env var reference for the projection API base URL",
    )
    endpoints: dict[str, str] = Field(
        default_factory=dict,
        description="Named endpoint path map (e.g. {'nodes': '/api/v1/nodes'})",
    )
    schema_version: str = Field(..., description="API schema version string")
    freshness_sla_ms: int = Field(
        ...,
        description="Maximum acceptable data freshness in milliseconds",
    )
