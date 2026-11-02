# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed empty state for a view section (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason

__all__ = ["ModelViewEmptyState"]


class ModelViewEmptyState(BaseModel):
    """Why a section has no rows. A section never blanks silently."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    reason: EnumEmptyStateReason = Field(
        ..., description="Typed reason the section has no rows"
    )
    detail: str | None = Field(
        default=None, min_length=1, description="Optional operator-facing detail"
    )
