# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure queries over a folded work ledger (OMN-19405, typed work ledger T4).

Every query reads typed fields of a ``ModelWorkLedgerState`` only and answers
with a ``ModelWorkLedgerVerdict``. A state that is not decidable answers
UNDECIDED to every query, never CLEAR. Exit codes: 0 CLEAR, 3 HELD or FOUND,
2 UNDECIDED.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_question_status import EnumQuestionStatus
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work.model_actor import ModelActor
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor
from omnibase_core.models.events.work.model_work_name_rules import normalize_work_name
from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)
from omnibase_core.models.nodes.work_ledger_state.model_stale_hold import (
    ModelStaleHold,
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
    "ROLL_INVARIANT_EXCLUDED_QUERIES",
    "STALE_HOLD_AGE",
    "actor_lane",
    "health",
    "hold_age",
    "holds",
    "inbox",
    "is_held",
    "is_stale_hold",
    "open_claims",
    "pauses_in_force",
    "questions",
    "surface_lease",
]

ROLL_INVARIANT_EXCLUDED_QUERIES: frozenset[str] = frozenset({"health"})
"""Queries the roll invariant ``fold(archive union live) == fold(live)`` does not cover.

``health`` counts lines, events and invalid releases. A roll moves closed events
into the archive, so ``line_count`` and ``event_count`` of the live fold differ
from those of the whole ledger whatever the roll carries, and carrying invalid
releases through the roll could not make ``health`` invariant. Every other query
answers the same from the live file alone. The roll's property test imports
this set rather than spelling the exclusion again.
"""

STALE_HOLD_AGE: timedelta = timedelta(days=14)
"""An open-ended hold nothing released is stale once it is older than this.

Settled operator rule (OMN-21947): an open-ended hold older than 14 days counts as stale.
"""

_CLEAR = EnumWorkLedgerVerdictStatus.CLEAR
_HELD = EnumWorkLedgerVerdictStatus.HELD
_FOUND = EnumWorkLedgerVerdictStatus.FOUND


def _undecided(state: ModelWorkLedgerState) -> ModelWorkLedgerVerdict:
    return ModelWorkLedgerVerdict(
        status=EnumWorkLedgerVerdictStatus.UNDECIDED,
        undecided_reasons=state.undecided_reasons,
    )


def hold_age(held: ModelHoldInForce, as_of: datetime) -> timedelta:
    """How long the hold has stood at ``as_of``."""
    return as_of - held.hold.emitted_at


def is_stale_hold(held: ModelHoldInForce, as_of: datetime) -> bool:
    """Open-ended (no ``expires_at``), never partly released, older than 14 days.

    A partial release is a release: a hold someone has already worked on is not abandoned.
    A surface lease carries an expiry and is judged by it, never by this rule.
    """
    return (
        held.hold.expires_at is None
        and not held.partial_releases
        and hold_age(held, as_of) > STALE_HOLD_AGE
    )


def _split_stale(
    state: ModelWorkLedgerState, as_of: datetime | None
) -> tuple[tuple[ModelHoldInForce, ...], tuple[ModelHoldInForce, ...]]:
    """The holds in force and the stale ones, apart. No clock: nothing is stale."""
    if as_of is None:
        return state.holds_in_force, ()
    in_force = tuple(h for h in state.holds_in_force if not is_stale_hold(h, as_of))
    stale = tuple(h for h in state.holds_in_force if is_stale_hold(h, as_of))
    return in_force, stale


def _hold_verdict(
    state: ModelWorkLedgerState,
    as_of: datetime | None,
    matches: Callable[[ModelHoldInForce], bool],
) -> ModelWorkLedgerVerdict:
    """HELD by the matching holds in force; the matching stale ones are listed apart."""
    in_force, stale = _split_stale(state, as_of)
    matching = tuple(held for held in in_force if matches(held))
    return ModelWorkLedgerVerdict(
        status=_HELD if matching else _CLEAR,
        holds=matching,
        stale_holds=_stale_entries(stale, matches, as_of),
    )


def _stale_entries(
    stale: tuple[ModelHoldInForce, ...],
    matches: Callable[[ModelHoldInForce], bool],
    as_of: datetime | None,
) -> tuple[ModelStaleHold, ...]:
    if as_of is None:
        return ()
    return tuple(
        ModelStaleHold(hold=held, age=hold_age(held, as_of))
        for held in stale
        if matches(held)
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
    *,
    as_of: datetime | None = None,
) -> ModelWorkLedgerVerdict:
    """Is ``action`` on ``pr`` held? ``runtime_affecting=None`` is treated as True.

    HELD cites every hold in force that blocks ``action``, applies to the PR's
    runtime class, covers the PR, and has not released it by a partial release.
    With ``as_of``, a stale hold (see ``is_stale_hold``) is not in force: it is
    listed in ``stale_holds`` with its age. Without it nothing is judged stale.
    """
    if not state.decidable:
        return _undecided(state)
    return _hold_verdict(
        state,
        as_of,
        lambda held: action in held.hold.blocks
        and _applies_to_class(held, runtime_affecting)
        and scope_covers_pr(held.hold.scope, pr)
        and not any(
            release.partial_scope is not None
            and scope_covers_pr(release.partial_scope, pr)
            for release in held.partial_releases
        ),
    )


def holds(
    state: ModelWorkLedgerState, *, as_of: datetime | None = None
) -> ModelWorkLedgerVerdict:
    """Every hold in force, and apart from them every stale hold with its age.

    The ``holds`` verb: HELD when any hold is in force, CLEAR otherwise. A stale hold
    never turns a CLEAR into HELD.
    """
    if not state.decidable:
        return _undecided(state)
    return _hold_verdict(state, as_of, lambda held: True)


def pauses_in_force(
    state: ModelWorkLedgerState,
    repo: str,
    runtime_affecting: bool | None,
    *,
    as_of: datetime | None = None,
) -> ModelWorkLedgerVerdict:
    """Repo-scope and all-repo holds still covering ``repo``, with their exemptions.

    ``runtime_affecting=None`` is treated as True. The partial releases on each
    returned hold are its exemptions (single PRs released from the pause). With
    ``as_of``, a stale hold is listed in ``stale_holds`` and does not pause anything.
    """
    if not state.decidable:
        return _undecided(state)
    return _hold_verdict(
        state,
        as_of,
        lambda held: _applies_to_class(held, runtime_affecting)
        and scope_covers_repo(held.hold.scope, repo)
        and not any(
            release.partial_scope is not None
            and scope_covers_repo(release.partial_scope, repo)
            for release in held.partial_releases
        ),
    )


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
        if (
            wanted_ticket is None
            or (
                claim.ticket_id is not None and claim.ticket_id.upper() == wanted_ticket
            )
        )
        and (pr is None or pr in claim.prs)
        and (
            lane is None
            or normalize_work_name(actor_lane(claim.actor)) == normalize_work_name(lane)
        )
    )
    return ModelWorkLedgerVerdict(
        status=_FOUND if matching else _CLEAR, claims=matching
    )


def inbox(
    state: ModelWorkLedgerState, lane: str, *, as_of: datetime | None = None
) -> ModelWorkLedgerVerdict:
    """Messages and holds addressed to ``lane`` that ``lane`` has not acknowledged.

    Also every hold in force whose scope names ``lane``, acknowledged or not:
    a hold on a lane binds it until a release lifts it. With ``as_of``, a stale hold
    is listed in ``stale_holds`` instead.
    """
    if not state.decidable:
        return _undecided(state)
    lane = normalize_work_name(lane)
    acked = {
        ack.re
        for ack in state.acks
        if normalize_work_name(actor_lane(ack.actor)) == lane
    }
    messages = tuple(
        message
        for message in state.messages
        if (message.to.all_lanes or lane in message.to.lanes)
        and message.event_id not in acked
    )

    def addressed(held: ModelHoldInForce) -> bool:
        return (
            held.hold.addressed_to is not None
            and (
                held.hold.addressed_to.all_lanes or lane in held.hold.addressed_to.lanes
            )
            and held.hold.event_id not in acked
        ) or (
            lane in held.hold.scope.lanes
            and not any(
                release.partial_scope is not None
                and lane in release.partial_scope.lanes
                for release in held.partial_releases
            )
        )

    in_force, stale = _split_stale(state, as_of)
    held_now = tuple(held for held in in_force if addressed(held))
    return ModelWorkLedgerVerdict(
        status=_FOUND if messages or held_now else _CLEAR,
        messages=messages,
        holds=held_now,
        stale_holds=_stale_entries(stale, addressed, as_of),
    )


def surface_lease(state: ModelWorkLedgerState, surface: str) -> ModelWorkLedgerVerdict:
    """Holds in force on ``surface``. An expired, unreleased lease still answers HELD."""
    if not state.decidable:
        return _undecided(state)
    surface = normalize_work_name(surface)
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


def questions(
    state: ModelWorkLedgerState,
    *,
    status: EnumQuestionStatus | None = EnumQuestionStatus.OPEN,
    ticket_id: str | None = None,
) -> ModelWorkLedgerVerdict:
    """Questions put to the operator, with the given status (None: any status).

    FOUND cites every matching question with its answers and withdrawals. Ticket
    ids compare case-insensitively. A question is ANSWERED only by a ruling or
    consent naming it, and WITHDRAWN only by a typed withdrawal naming it; the
    question's text and every summary are never read.
    """
    if not state.decidable:
        return _undecided(state)
    wanted_ticket = None if ticket_id is None else ticket_id.upper()
    matching = tuple(
        entry
        for entry in state.questions
        if (status is None or entry.status is status)
        and (
            wanted_ticket is None
            or (
                entry.question.ticket_id is not None
                and entry.question.ticket_id.upper() == wanted_ticket
            )
        )
    )
    return ModelWorkLedgerVerdict(
        status=_FOUND if matching else _CLEAR, questions=matching
    )


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
        open_question_count=sum(
            1 for entry in state.questions if entry.status is EnumQuestionStatus.OPEN
        ),
        invalid_question_ref_count=len(state.invalid_question_refs),
        undecided_reasons=state.undecided_reasons,
    )
