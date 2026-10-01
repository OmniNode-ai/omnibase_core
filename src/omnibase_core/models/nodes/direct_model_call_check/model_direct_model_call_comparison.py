# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallComparison: findings matched to a baseline (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding import (
    ModelDirectModelCallFinding,
)

__all__ = ["ModelDirectModelCallComparison"]


class ModelDirectModelCallComparison(BaseModel):
    """The ratchet verdict: what is new, what is stale, what has expired."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    new: tuple[ModelDirectModelCallFinding, ...] = Field(
        description="Sites no live entry covers"
    )
    stale: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        description="Entries that match no site"
    )
    expired: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        description="Entries past their expiry"
    )
