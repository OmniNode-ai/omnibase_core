# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeWorkLedgerStateCompute: the work-ledger fold (OMN-19405, typed work ledger T4).

Folds the lines of a JSON-lines work ledger into a ``ModelWorkLedgerState``:
the holds in force, the refused releases, the open claims, and the messages and
acknowledgements an inbox is computed from.

Architecture: COMPUTE node on the def-B ``handle(request) -> response`` shape
(OMN-14355). Pure and deterministic: no file, clock, environment or bus access,
and no envelope. Reading the ledger file is the read CLI's effect boundary.

Fold semantics, all set-based so the result does not depend on line order:

- A hold is in force unless valid releases naming its event_id cover its whole
  scope: one full release, or partial releases whose scopes together cover it.
- A partial release subtracts exactly its typed ``partial_scope``. A partial
  scope reaching outside the hold's scope releases nothing and is listed.
- A release naming an unknown event_id, or an event that is not a hold,
  releases nothing and is listed. So is a reap of a hold that is not a lease,
  and a release that lifts a surface without recording the surface outcome.
- A claim is open until a ``work.claim.released`` names it or a
  ``work.result.recorded`` lists it in ``closes_claims``.
- Identical duplicate event_ids count once. A duplicate event_id with
  different content makes the ledger UNDECIDED.
- An unparseable line (including an unknown schema or kind) or a ledger with no
  ``work.ledger.epoch.opened`` event makes the ledger UNDECIDED.

Free-text fields (``summary``, ``operator_words``, ``until_text``,
``scope_text``, ``verdict``) are never read here.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime

from omnibase_core.enums.enum_invalid_release_reason import EnumInvalidReleaseReason
from omnibase_core.errors.error_work_ledger_parse import WorkLedgerParseError
from omnibase_core.models.events.work.model_work_claim_released import (
    ModelWorkClaimReleased,
)
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_event_union import ModelWorkEvent
from omnibase_core.models.events.work.model_work_hold_placed import ModelWorkHoldPlaced
from omnibase_core.models.events.work.model_work_hold_released import (
    ModelWorkHoldReleased,
)
from omnibase_core.models.events.work.model_work_ledger_epoch_opened import (
    ModelWorkLedgerEpochOpened,
)
from omnibase_core.models.events.work.model_work_ledger_line import (
    dump_work_ledger_line,
    parse_work_ledger_line,
)
from omnibase_core.models.events.work.model_work_ledger_record import (
    WORK_LEDGER_SCHEMA,
    ModelWorkLedgerRecord,
)
from omnibase_core.models.events.work.model_work_message_acked import (
    ModelWorkMessageAcked,
)
from omnibase_core.models.events.work.model_work_message_sent import (
    ModelWorkMessageSent,
)
from omnibase_core.models.events.work.model_work_result_recorded import (
    ModelWorkResultRecorded,
)
from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)
from omnibase_core.models.nodes.work_ledger_state.model_invalid_release import (
    ModelInvalidRelease,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_fold_input import (
    ModelWorkLedgerFoldInput,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_state import (
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute.scope_math import (
    is_subscope,
    scopes_cover_scope,
)

__all__ = [
    "NO_EPOCH_REASON",
    "NodeWorkLedgerStateCompute",
    "complete_ledger_lines",
    "fold_work_events",
]

NO_EPOCH_REASON = "no work.ledger.epoch.opened event: the typed cutover is not done"


def complete_ledger_lines(text: str) -> tuple[str, ...]:
    """Split ledger text into complete lines, leaving out an unterminated tail.

    A final line with no newline is an append whose writer has not finished.
    Leaving it out is the same as reading the file a moment earlier; treating
    it as a parse failure would make every in-progress append read UNDECIDED.
    A blank line in the middle is kept, and fails to parse.
    """
    if not text:
        return ()
    parts = text.split("\n")
    # The element after the last newline is "" when the text ends with a
    # newline, and an unterminated fragment otherwise: either way it is dropped.
    return tuple(parts[:-1])


def _canonical(event: ModelWorkEvent) -> str:
    return dump_work_ledger_line(
        ModelWorkLedgerRecord.model_validate(
            {"schema": WORK_LEDGER_SCHEMA, "event": event}
        )
    )


def _by_id(event: ModelWorkEvent) -> str:
    return str(event.event_id)


def _release_refusal(
    release: ModelWorkHoldReleased, target: ModelWorkEvent | None
) -> EnumInvalidReleaseReason | None:
    """Why ``release`` releases nothing, or None when it is valid."""
    if target is None:
        return EnumInvalidReleaseReason.UNKNOWN_HOLD
    if not isinstance(target, ModelWorkHoldPlaced):
        return EnumInvalidReleaseReason.NOT_A_HOLD
    if release.reap and target.expires_at is None:
        return EnumInvalidReleaseReason.REAP_WITHOUT_LEASE
    partial = release.partial_scope
    if partial is not None and not is_subscope(partial, target.scope):
        return EnumInvalidReleaseReason.NOT_SUBSET
    lifts_surface = bool(target.scope.surfaces if partial is None else partial.surfaces)
    if lifts_surface and release.surface_result is None:
        return EnumInvalidReleaseReason.MISSING_SURFACE_RESULT
    return None


def fold_work_events(
    events: Iterable[ModelWorkEvent],
    *,
    as_of: datetime | None = None,
    line_count: int | None = None,
    undecided_reasons: Sequence[str] = (),
) -> ModelWorkLedgerState:
    """Fold typed work events into the ledger state. Pure; order does not matter.

    Args:
        events: The parsed events, in any order, duplicates allowed.
        as_of: Instant at which a surface lease's expiry is judged.
        line_count: Lines the events came from; defaults to the event count.
        undecided_reasons: Doubts found before folding, such as unparseable lines.
    """
    reasons: set[str] = set(undecided_reasons)
    by_id: dict[uuid.UUID, ModelWorkEvent] = {}
    seen = 0
    for event in events:
        seen += 1
        prior = by_id.get(event.event_id)
        if prior is None:
            by_id[event.event_id] = event
            continue
        if prior == event:
            continue
        prior_line, event_line = _canonical(prior), _canonical(event)
        if prior_line == event_line:
            continue
        reasons.add(f"conflicting duplicate event_id {event.event_id}")
        # Keep one content deterministically, so the state still does not
        # depend on line order; the ledger is UNDECIDED either way.
        if event_line < prior_line:
            by_id[event.event_id] = event

    distinct = sorted(by_id.values(), key=_by_id)
    holds = [e for e in distinct if isinstance(e, ModelWorkHoldPlaced)]
    releases = [e for e in distinct if isinstance(e, ModelWorkHoldReleased)]
    epochs = [e for e in distinct if isinstance(e, ModelWorkLedgerEpochOpened)]

    fully_released: set[uuid.UUID] = set()
    partials: dict[uuid.UUID, list[ModelWorkHoldReleased]] = {}
    invalid: list[ModelInvalidRelease] = []
    for release in releases:
        refusal = _release_refusal(release, by_id.get(release.releases))
        if refusal is not None:
            invalid.append(ModelInvalidRelease(release=release, reason=refusal))
        elif release.partial_scope is None:
            fully_released.add(release.releases)
        else:
            partials.setdefault(release.releases, []).append(release)

    in_force: list[ModelHoldInForce] = []
    for hold in holds:
        if hold.event_id in fully_released:
            continue
        applied = partials.get(hold.event_id, [])
        if scopes_cover_scope(
            [release.partial_scope for release in applied if release.partial_scope],
            hold.scope,
        ):
            continue
        in_force.append(
            ModelHoldInForce(
                hold=hold,
                partial_releases=tuple(applied),
                expired_unreleased=(
                    hold.expires_at is not None
                    and as_of is not None
                    and as_of >= hold.expires_at
                ),
            )
        )

    closed_claims: set[uuid.UUID] = set()
    for event in distinct:
        if isinstance(event, ModelWorkClaimReleased):
            closed_claims.add(event.claim_event_id)
        elif isinstance(event, ModelWorkResultRecorded):
            closed_claims.update(event.closes_claims)

    if not epochs:
        reasons.add(NO_EPOCH_REASON)

    return ModelWorkLedgerState(
        line_count=seen if line_count is None else line_count,
        event_count=len(distinct),
        undecided_reasons=tuple(sorted(reasons)),
        epoch=(
            max(epochs, key=lambda e: (e.epoch_seq, str(e.event_id)))
            if epochs
            else None
        ),
        last_event_at=max((e.emitted_at for e in distinct), default=None),
        holds_in_force=tuple(in_force),
        invalid_releases=tuple(invalid),
        open_claims=tuple(
            e
            for e in distinct
            if isinstance(e, ModelWorkClaimRequested)
            and e.event_id not in closed_claims
        ),
        messages=tuple(e for e in distinct if isinstance(e, ModelWorkMessageSent)),
        acks=tuple(e for e in distinct if isinstance(e, ModelWorkMessageAcked)),
    )


class NodeWorkLedgerStateCompute:
    """COMPUTE handler that folds work-ledger lines into a ``ModelWorkLedgerState``."""

    def handle(self, input_model: ModelWorkLedgerFoldInput) -> ModelWorkLedgerState:
        """Definition-B canonical entry point (OMN-14355). Pure: no I/O, no clock."""
        events: list[ModelWorkEvent] = []
        reasons: list[str] = []
        for number, raw in enumerate(input_model.lines, start=1):
            try:
                events.append(parse_work_ledger_line(raw).event)
            except WorkLedgerParseError as exc:
                reasons.append(f"line {number} does not parse: {exc}")
        return fold_work_events(
            events,
            as_of=input_model.as_of,
            line_count=len(input_model.lines),
            undecided_reasons=reasons,
        )
