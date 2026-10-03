# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Input contract for the sprint-roll COMPUTE node (OMN-20396).

The node is pure/deterministic/no-I/O: every fact it needs arrives here. The I/O-derived
inputs are resolved at the caller/EFFECT boundary (OMN-20397), never in the handler:

* `sprints` -- the sprint window, chronological. The board's own sprint read returns
  only the current and future sprints, so the boundary resolves the sprint to drain from
  the project list FIRST and loads the window from there; a window that starts after the
  drained sprint makes a Monday run unable to see what it is draining.
* `criteria` and `criteria_text` -- the release-criterion carrier lists and wording,
  owned by omninode_infra's `tools/beta_board/beta_board_data.py`. Passed in rather than
  imported so the node stays pure and so a second copy of the carrier lists cannot
  disagree with the board the week it drifts.
* `as_of` -- the run date, from the clock at the boundary.

`closed_states` and `state_rank` are inputs rather than constants because Linear
workflow states are workspace-configurable; hard-coding them would make the node wrong
for any team that renames a state rather than merely unsupported.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_capacity_unit import EnumCapacityUnit
from omnibase_core.models.nodes.sprint_roll.model_sprint import ModelSprint

__all__ = ["ModelSprintRollRequest"]

#: In Review is one step from done, so it takes the earliest slot; In Progress follows;
#: anything else sorts after both.
DEFAULT_STATE_RANK: dict[str, int] = {"In Review": 0, "In Progress": 1}
DEFAULT_CLOSED_STATES: frozenset[str] = frozenset(
    {"Done", "Canceled", "Cancelled", "Completed"}
)
#: A meta-criterion's wording matches any ticket that mentions a gate, a ticket or a
#: sprint, so it is never a text-fallback target. C27 is "every gate row in section 7.1
#: has a ticket in the beta sprint, or a recorded ruling that retires it".
DEFAULT_META_CRITERIA: frozenset[str] = frozenset({"C27"})


class ModelSprintRollRequest(BaseModel):
    """Typed, side-effect-free request for a sprint roll plan."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sprints: tuple[ModelSprint, ...]
    as_of: dt.date
    capacity_unit: EnumCapacityUnit = EnumCapacityUnit.TICKETS
    cap_override: int | None = None
    criteria: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    criteria_text: dict[str, str] = Field(default_factory=dict)
    meta_criteria: frozenset[str] = DEFAULT_META_CRITERIA
    closed_states: frozenset[str] = DEFAULT_CLOSED_STATES
    state_rank: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_STATE_RANK))
