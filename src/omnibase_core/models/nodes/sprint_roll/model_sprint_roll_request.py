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
from uuid import UUID

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
    capacity_unit: EnumCapacityUnit = EnumCapacityUnit.POINTS
    cap_override: int | None = None
    criteria: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    criteria_text: dict[str, str] = Field(default_factory=dict)
    meta_criteria: frozenset[str] = DEFAULT_META_CRITERIA
    closed_states: frozenset[str] = DEFAULT_CLOSED_STATES
    state_rank: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_STATE_RANK))

    #: Tickets that MUST be placed in the first target sprint, cap or no cap. The
    #: independent walks are the case this exists for: a walk is the only evidence that
    #: someone who did not build a thing exercised it, so a cap may not silently defer
    #: one -- the 2026-10-04 dry run put all three delegation walks in Backlog. A
    #: mandatory ticket is placed before the cap is consulted and its size still counts
    #: against the load, so the overflow lands on ordinary work rather than on proof.
    mandatory: frozenset[str] = frozenset()

    #: Per-owner ceiling inside one sprint, in the same unit as the cap. A team-wide cap
    #: alone is satisfied while one person carries the whole sprint: on the 2026-10-04
    #: window the 10-12 sprint came to 42 of its 46 points on a single owner, with two
    #: of the three pillars untouched. None leaves the team cap as the only limit.
    owner_cap: int | None = None

    #: Ticket identifier -> pillar name, resolved at the boundary. The node does not
    #: classify: a pillar comes from the ticket's criterion or its own wording, both of
    #: which are the caller's facts, and a ticket with no entry is placed without a
    #: floor claim.
    pillar_of: dict[str, str] = Field(default_factory=dict)

    #: Minimum tickets per pillar per sprint, filled before the general pass. A sprint
    #: that ships one pillar and starves another reads as progress and is not: the first
    #: cascade run produced a 36-of-46-point Dashboard sprint with zero Delegation.
    #: Zero disables the floor.
    pillar_floor: int = 0

    #: Sprints that may RECEIVE rolled work, when only some of the following sprints are
    #: valid targets. The M4.5 bucket is the case: it is a parked fast-follow list, not
    #: next week's plan, and rebalancing it to the cap moved 20 tickets into it and
    #: pushed 26 out. Empty means every sprint after the source is a target.
    target_sprint_ids: frozenset[UUID] = frozenset()

    #: Tickets whose children carry the points. A parent gets no proposed estimate --
    #: estimating both it and its children double-counts the work -- and is reported in
    #: the plan instead, so a blank parent reads as a decision rather than an omission.
    #: On the 2026-10-04 window these were OMN-17013 and OMN-17679 with ten children
    #: each, and OMN-17356 and OMN-17360 with two.
    parents: frozenset[str] = frozenset()
