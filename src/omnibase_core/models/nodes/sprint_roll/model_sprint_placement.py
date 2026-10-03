# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""What one sprint holds after a roll (OMN-20396).

`moved_in` lists only the tickets whose sprint actually changes, so a rebalance that
leaves a ticket where it already sits is not reported as a move. `load_after` is
compared against the plan's `cap` by the caller rather than stored as an over-by here:
a figure derived from a cap must not outlive a change to it.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelSprintPlacement"]


class ModelSprintPlacement(BaseModel):
    """One sprint's contents after the roll."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sprint_id: UUID
    name: str
    load_before: int
    load_after: int
    ticket_ids: tuple[str, ...] = Field(default_factory=tuple)
    moved_in: tuple[str, ...] = Field(default_factory=tuple)
