# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dashboard connection contract model for delegation runtime configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_delegation_projection_api import (
    ModelDelegationProjectionApi,
)


class ModelDelegationDashboardConnection(BaseModel):
    """Dashboard connection configuration backed by the projection API."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    projection_api_ref: ModelDelegationProjectionApi = Field(
        ...,
        description="Projection API configuration this dashboard connects to",
    )
    refresh_contract: dict[str, int] = Field(
        default_factory=dict,
        description="Refresh timing contract (e.g. {'interval_ms': 30000})",
    )
