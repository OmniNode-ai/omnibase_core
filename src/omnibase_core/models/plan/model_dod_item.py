# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Minimal DoD item model for plan success criteria.

Used by ModelPlanContract.success_criteria as the type-safe representation
of a single definition-of-done item. Structured evidence types and richer
lifecycle live in ModelProofRequirement (ticket contract territory); this
model is deliberately flat.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDoDItem", "DoDItem"]


class ModelDoDItem(BaseModel):
    """A single definition-of-done item on a plan contract.

    Flat, frozen, append-only. For richer evidence semantics see
    ModelProofRequirement on ticket contracts.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    id: str = Field(..., min_length=1, description="Stable DoD item identifier.")
    description: str = Field(
        ..., min_length=1, description="Human-readable DoD statement."
    )
    evidence_type: str | None = Field(
        default=None,
        description=(
            "Evidence kind expected to satisfy this item "
            "(e.g. 'rendered_output', 'integration_test', 'screenshot'). "
            "None means unspecified."
        ),
    )
    satisfied: bool = Field(
        default=False, description="Whether this DoD item has been satisfied."
    )


DoDItem = ModelDoDItem
