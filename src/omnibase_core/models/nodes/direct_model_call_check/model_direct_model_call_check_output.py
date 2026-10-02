# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallCheckOutput: the gate's verdict (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding import (
    ModelDirectModelCallFinding,
)

__all__ = ["ModelDirectModelCallCheckOutput"]


class ModelDirectModelCallCheckOutput(BaseModel):
    """Every site, and what the shrink-only ratchet makes of them."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelDirectModelCallFinding, ...] = Field(
        description="Every direct model call site outside the sanctioned packages"
    )
    new: tuple[ModelDirectModelCallFinding, ...] = Field(
        default=(), description="Sites no live baseline entry covers"
    )
    stale: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        default=(), description="Entries that no longer match a site"
    )
    expired: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        default=(), description="Entries past their expiry"
    )
    grown: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        default=(), description="Entries added or widened against base_ref"
    )
    problems: tuple[str, ...] = Field(
        default=(), description="Other refusals: wrong ticket, re-created baseline"
    )
    notes: tuple[str, ...] = Field(default=(), description="Informational lines")
    passed: bool = Field(description="True when nothing above refuses the change")
