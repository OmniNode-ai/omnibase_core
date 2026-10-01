# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallBaseline: the committed baseline document: a multiset of tolerated sites (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)

__all__ = ["ModelDirectModelCallBaseline"]


class ModelDirectModelCallBaseline(BaseModel):
    """The committed baseline document: a multiset of tolerated sites."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Baseline schema version")
    entries: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        default=(), description="Tolerated pre-existing sites"
    )
