# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One edge of a workflow's reachable product graph (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWalkStep(BaseModel):
    """One fired edge: product state before, the trigger, product state after.

    A product state holds one state per component, in the workflow's
    component order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    from_state: tuple[str, ...] = Field(
        description="Product state before the edge, one entry per component"
    )
    trigger: str = Field(description="Declared trigger that fires the edge")
    to_state: tuple[str, ...] = Field(
        description="Product state after the edge, one entry per component"
    )
