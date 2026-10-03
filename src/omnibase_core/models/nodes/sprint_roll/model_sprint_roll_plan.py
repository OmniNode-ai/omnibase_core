# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Output contract for the sprint-roll COMPUTE node (OMN-20396).

A plan, not an action. Nothing here has been written anywhere: the paired EFFECT node
(OMN-20397) turns `placements` into project moves and `backlog_ticket_ids` into state
moves, journalling each one before it sends it.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.sprint_roll.model_criterion_proposal import (
    ModelCriterionProposal,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_placement import (
    ModelSprintPlacement,
)

__all__ = ["ModelSprintRollPlan"]


class ModelSprintRollPlan(BaseModel):
    """The whole roll: where every open ticket in the window lands."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_sprint_id: UUID
    source_sprint_name: str
    cap: int
    cap_basis: str
    median_estimate: int
    rolling_ticket_ids: tuple[str, ...] = Field(default_factory=tuple)
    placements: tuple[ModelSprintPlacement, ...] = Field(default_factory=tuple)
    backlog_ticket_ids: tuple[str, ...] = Field(default_factory=tuple)
    proposals: tuple[ModelCriterionProposal, ...] = Field(default_factory=tuple)
