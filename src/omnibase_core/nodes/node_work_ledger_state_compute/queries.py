# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure queries over a folded work ledger (OMN-19405, typed work ledger T4).

Every query reads typed fields of a ``ModelWorkLedgerState`` only and answers
with a ``ModelWorkLedgerVerdict``. A state that is not decidable answers
UNDECIDED to every query, never CLEAR. Exit codes: 0 CLEAR, 3 HELD or FOUND,
2 UNDECIDED.
"""

from __future__ import annotations

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work.model_actor import ModelActor
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor
from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_health import (
    ModelWorkLedgerHealth,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_state import (
    ModelWorkLedgerState,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_verdict import (
    ModelWorkLedgerVerdict,
)
from omnibase_core.nodes.node_work_ledger_state_compute.scope_math import (
    scope_covers_pr,
    scope_covers_repo,
)

__all__ = [
    "actor_lane",
    "health",
    "inbox",
    "is_held",
    "open_claims",
    "pauses_in_force",
    "surface_lease",
]

_CLEAR = EnumWorkLedgerVerdictStatus.CLEAR
_HELD = EnumWorkLedgerVerdictStatus.HELD
_FOUND = EnumWorkLedgerVerdictStatus.FOUND


def _undecided(state: ModelWorkLedgerState) -> ModelWorkLedgerVerdict:
    return ModelWorkLedgerVerdict(
        status=EnumWorkLedgerVerdictStatus.UNDECIDED,
        undecided_reasons=state.undecided_reasons,
    )


def _applies_to_class(held: ModelHoldInForce, runtime_affecting: bool | None) -> bool:
    """A runtime-only hold applies to runtime PRs; an unknown class counts as runtime."""
    return not held.hold.runtime_only or runtime_affecting is not False


def actor_lane(actor: ModelActor) -> str:
    """The lane name an actor answers to: a session's handle, else its actor_key."""
    if isinstance(actor, ModelSessionActor):
        return actor.session_handle
    return actor.actor_key


def is_held(
    state: ModelWorkLedgerState,
    pr: ModelPrKey,
    action: EnumHoldBlock,
    runtime_affecting: bool | None,
) -> ModelWorkLedgerVerdict:
    """Is ``action`` on ``pr`` held? ``runtime_affecting=None`` is treated as True.

    HELD cites every hold in force that blocks ``action``, applies to the PR's
    runtime class, covers the PR, and has not released it by a partial release.
    """
    if not state.decidable:
        return _undecided(state)
    matching = tuple(
        held
        for held in state.holds_in_force
        if action in held.hold.blocks
        and _applies_to_class(held, runtime_affecting)
        and scope_covers_pr(held.hold.scope, pr)
        and not any(
            release.partial_scope is not None
            and scope_covers_pr(release.partial_scope, pr)
            for release in held.partial_releases
        )
    )
    return ModelWorkLedgerVerdict(status=_HELD if matching else _CLEAR, holds=matching)


def pauses_in_force(
    state: ModelWorkLedgerState, repo: str, runtime_affecting: bool | None
) -> ModelWorkLedgerVerdict:
    """Repo-scope and all-repo holds still covering ``repo``, with their exemptions.

    ``runtime_affecting=None`` is treated as True. The partial releases on each
    returned hold are its exemptions (single PRs released from the pause).
    """
    if not state.decidable:
        return _undecided(state)
    matching = tuple(
        held
        for held in state.holds_in_force
        if _applies_to_class(held, runtime_affecting)
        and scope_covers_repo(held.hold.scope, repo)
        and not any(
            release.partial_scope is not None
            and scope_covers_repo(release.partial_scope, repo)
            for release in held.partial_releases
        )
    )
    return ModelWorkLedgerVerdict(status=_HELD if matching else _CLEAR, holds=matching)


def open_claims(
    state: ModelWorkLedgerState,
    *,
    ticket_id: str | None = None,
    pr: ModelPrKey | None = None,
    lane: str | None = None,
) -> ModelWorkLedgerVerdict:
    """Open claims matching every filter given. Ticket ids compare case-insensitively."""
    if not state.decidable:
        return _undecided(state)
    wanted_ticket = None if ticket_id is None else ticket_id.upper()
    matching = tuple(
        claim
        for claim in state.open_claims
        if (wanted_ticket is None or claim.ticket_id.upper() == wanted_ticket)
        and (pr is None or pr in claim.prs)
        and (lane is None or actor_lane(claim.actor) == lane)
    )
    return ModelWorkLedgerVerdict(
        status=_FOUND if matching else _CLEAR, claims=matching
    )


def inbox(state: ModelWorkLedgerState, lane: str) -> ModelWorkLedgerVerdict:
    """Messages and holds addressed to ``lane`` that ``lane`` has not acknowledged.

    Also every hold in force whose scope names ``lane``, acknowledged or not:
    a hold on a lane binds it until a release lifts it.
    """
    if not state.decidable:
        return _undecided(state)
    acked = {ack.re for ack in state.acks if actor_lane(ack.actor) == lane}
    messages = tuple(
        message
        for message in state.messages
        if (message.to.all_lanes or lane in message.to.lanes)
        and message.event_id not in acked
    )
    holds = tuple(
        held
        for held in state.holds_in_force
        if (
            held.hold.addressed_to is not None
            and (
                held.hold.addressed_to.all_lanes or lane in held.hold.addressed_to.lanes
            )
            and held.hold.event_id not in acked
        )
        or (
            lane in held.hold.scope.lanes
            and not any(
                release.partial_scope is not None
                and lane in release.partial_scope.lanes
                for release in held.partial_releases
            )
        )
    )
    return ModelWorkLedgerVerdict(
        status=_FOUND if messages or holds else _CLEAR,
        messages=messages,
        holds=holds,
    )


def surface_lease(state: ModelWorkLedgerState, surface: str) -> ModelWorkLedgerVerdict:
    """Holds in force on ``surface``. An expired, unreleased lease still answers HELD."""
    if not state.decidable:
        return _undecided(state)
    matching = tuple(
        held
        for held in state.holds_in_force
        if surface in held.hold.scope.surfaces
        and not any(
            release.partial_scope is not None
            and surface in release.partial_scope.surfaces
            for release in held.partial_releases
        )
    )
    return ModelWorkLedgerVerdict(status=_HELD if matching else _CLEAR, holds=matching)


def health(state: ModelWorkLedgerState) -> ModelWorkLedgerHealth:
    """Counts, the last event time, the epoch and the reasons for doubt."""
    return ModelWorkLedgerHealth(
        line_count=state.line_count,
        event_count=state.event_count,
        last_event_at=state.last_event_at,
        epoch_event_id=None if state.epoch is None else state.epoch.event_id,
        epoch_seq=None if state.epoch is None else state.epoch.epoch_seq,
        holds_in_force_count=len(state.holds_in_force),
        invalid_release_count=len(state.invalid_releases),
        undecided_reasons=state.undecided_reasons,
    )
