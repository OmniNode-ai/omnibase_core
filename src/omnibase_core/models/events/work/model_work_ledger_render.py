# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Render one work event as one row of the md work ledger (OMN-16182, plan T6).

The JSON-lines ledger is the truth. The md ledger is a view of it, written one
row per event, so every reader of the md (the row grammar, the claim index, the
decisions register, a human) keeps working after the cutover. Each rendered row
uses the md row grammar (OMN-19256, ``ledger-row-grammar/1``)::

    <emitted_at> | <TYPE> | lane=<lane> | ... | event=<event_id> | src=typed | <summary>

- The type cell follows the plan's section 5.1 mapping (``ROW_TYPE_BY_KIND``).
  The epoch event renders the ``EPOCH`` banner row, which the grammar exempts as
  a tool-written type.
- HOLD, MSG and ACK carry ``id=<emitted_at>-<lane>``, the grammar's id rule.
- ``event=<uuid>`` then ``src=typed`` mark the row as typed. ``render --check``
  and ``render --repair`` key on the ``event=`` cell.
- A reference the grammar spells as a row id or a row timestamp (``re=`` on an
  ACK or a RELEASE, ``to=`` on an ACK, ``closes-CLAIM=`` on a TERMINAL) is
  resolved through ``index``, the events the caller has read. The typed
  reference also appears as a ``*-event=`` cell. A reference the index cannot
  resolve raises ``WorkLedgerRenderError``; the renderer never guesses.

Free text (summaries, operator words, scope and until text) is collapsed onto
one line and a ``|`` in it becomes ``¦``, so it stays one cell. Operator words
are quoted with ``"`` unless they contain one, then with curly quotes. The
JSON-lines record keeps every byte verbatim; the row is a view.

The renderer checks what it can see structurally. Text guards that read the
whole row against the ledger (the consent-marker refusal on a MSG, the ruling
guard, the cost-sentence guard) stay with the appender, which runs them on the
rendered row before anything is written.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Final

from omnibase_core.enums.enum_actor_kind import EnumActorKind
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.governance.enum_pr_state import EnumPRState
from omnibase_core.errors.error_work_ledger_render import WorkLedgerRenderError
from omnibase_core.models.events.work.model_actor import ModelActor
from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_pr_ref import ModelPrRef
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor
from omnibase_core.models.events.work.model_work_claim_released import (
    ModelWorkClaimReleased,
)
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.events.work.model_work_correction_recorded import (
    ModelWorkCorrectionRecorded,
)
from omnibase_core.models.events.work.model_work_event_union import ModelWorkEvent
from omnibase_core.models.events.work.model_work_friction_recorded import (
    ModelWorkFrictionRecorded,
)
from omnibase_core.models.events.work.model_work_hold_placed import (
    ModelWorkHoldPlaced,
)
from omnibase_core.models.events.work.model_work_hold_released import (
    ModelWorkHoldReleased,
)
from omnibase_core.models.events.work.model_work_ledger_epoch_opened import (
    ModelWorkLedgerEpochOpened,
)
from omnibase_core.models.events.work.model_work_ledger_line import (
    dump_work_ledger_line,
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
from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    ModelWorkOperatorConsentRecorded,
)
from omnibase_core.models.events.work.model_work_result_recorded import (
    ModelWorkResultRecorded,
)
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)
from omnibase_core.models.events.work.model_work_status_recorded import (
    ModelWorkStatusRecorded,
)

__all__ = [
    "EPOCH_BANNER_ROW_TYPE",
    "ROW_TYPE_BY_KIND",
    "TYPED_SOURCE_CELL",
    "index_events",
    "render_ledger_row",
]

EPOCH_BANNER_ROW_TYPE: Final = "EPOCH"
"""Type cell of the epoch banner row. Tool-written, so the grammar exempts it."""

TYPED_SOURCE_CELL: Final = "src=typed"
"""The cell that marks a row as rendered from a typed event."""

ROW_TYPE_BY_KIND: Final[Mapping[EnumWorkEventKind, str]] = MappingProxyType(
    {
        EnumWorkEventKind.CLAIM_REQUESTED: "CLAIM",
        EnumWorkEventKind.STATUS_RECORDED: "STATUS",
        EnumWorkEventKind.RESULT_RECORDED: "TERMINAL",
        EnumWorkEventKind.FRICTION_RECORDED: "FRICTION",
        EnumWorkEventKind.CORRECTION_RECORDED: "CORRECTION",
        EnumWorkEventKind.RULING_RECORDED: "RULING",
        EnumWorkEventKind.CONSENT_RECORDED: "OPERATOR-CONSENT",
        EnumWorkEventKind.MESSAGE_SENT: "MSG",
        EnumWorkEventKind.MESSAGE_ACKED: "ACK",
        EnumWorkEventKind.HOLD_PLACED: "HOLD",
        EnumWorkEventKind.HOLD_RELEASED: "RELEASE",
        EnumWorkEventKind.CLAIM_RELEASED: "RELEASE",
        EnumWorkEventKind.LEDGER_EPOCH_OPENED: EPOCH_BANNER_ROW_TYPE,
    }
)
"""The md row type of every kind: plan section 5.1, one-to-one with OMN-19256."""

_ID_BEARING_TYPES: Final = frozenset({"HOLD", "MSG", "ACK"})
_STAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
# The grammar's lane token (ledger_grammar.LANE_TOKEN): what lane=, from=, to=
# parts and the tail of an id may hold.
_LANE_TOKEN_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_CELL_BAR: Final = "¦"  # broken bar: a '|' inside free text stays one cell


def index_events(
    events: Iterable[ModelWorkEvent],
) -> Mapping[uuid.UUID, ModelWorkEvent]:
    """Index events by event_id for reference resolution.

    An identical duplicate counts once. Two events with one id and different
    content raise ``WorkLedgerRenderError``: which one a reference names is
    undecidable, so nothing is rendered from either.
    """
    index: dict[uuid.UUID, ModelWorkEvent] = {}
    canonical: dict[uuid.UUID, str] = {}
    for event in events:
        line = _canonical(event)
        seen = canonical.get(event.event_id)
        if seen is None:
            index[event.event_id] = event
            canonical[event.event_id] = line
        elif seen != line:
            raise WorkLedgerRenderError(
                f"conflicting duplicate event_id {event.event_id}: two events share it "
                "with different content"
            )
    return MappingProxyType(index)


def render_ledger_row(
    event: ModelWorkEvent, index: Mapping[uuid.UUID, ModelWorkEvent]
) -> str:
    """Render ``event`` as its one md row, with no trailing newline.

    ``index`` holds the events the row may reference (``index_events``). Raises
    ``WorkLedgerRenderError`` when the row cannot be rendered in the grammar.
    """
    stamp = _stamp(event.emitted_at)
    lane = _lane(event.actor)
    row_type = ROW_TYPE_BY_KIND[event.kind]
    cells: list[str] = [stamp, row_type, f"lane={lane}"]
    if row_type in {"MSG", "ACK"}:
        cells.append(f"from={lane}")

    body: list[str]
    if isinstance(event, ModelWorkClaimRequested):
        body = _claim_cells(event)
    elif isinstance(event, ModelWorkClaimReleased):
        body = _claim_release_cells(event, index)
    elif isinstance(event, ModelWorkHoldPlaced):
        body = _hold_cells(event, stamp, lane)
    elif isinstance(event, ModelWorkHoldReleased):
        body = _hold_release_cells(event, index)
    elif isinstance(event, ModelWorkMessageSent):
        body = _message_cells(event, stamp, lane, index)
    elif isinstance(event, ModelWorkMessageAcked):
        body = _ack_cells(event, stamp, lane, index)
    elif isinstance(event, ModelWorkStatusRecorded):
        body = _status_cells(event)
    elif isinstance(event, ModelWorkResultRecorded):
        body = _result_cells(event, index)
    elif isinstance(event, ModelWorkFrictionRecorded):
        body = _friction_cells(event)
    elif isinstance(event, ModelWorkCorrectionRecorded):
        body = _correction_cells(event)
    elif isinstance(event, ModelWorkRulingRecorded):
        body = _ruling_cells(event)
    elif isinstance(event, ModelWorkOperatorConsentRecorded):
        body = _consent_cells(event)
    else:
        body = _epoch_cells(event)

    cells.extend(body)
    cells.extend([f"event={event.event_id}", TYPED_SOURCE_CELL, _text(event.summary)])
    return " | ".join(cells)


# ----------------------------------------------------------------- per kind


def _claim_cells(event: ModelWorkClaimRequested) -> list[str]:
    cells = [f"actor={_one_token(event.actor_key)}", f"ticket={event.ticket_id}"]
    if event.prs:
        cells.append(f"pr={_pr_keys(event.prs)}")
    if event.consent_ref is not None:
        cells.append(f"consent-event={event.consent_ref}")
    if event.scope_text is not None:
        cells.append(f"scope={_text(event.scope_text)}")
    if event.est_lane_hours is not None:
        displaces = "nothing" if event.displaces is None else _text(event.displaces)
        cells.append(
            f"est ~{_decimal(event.est_lane_hours)} lane-hours; "
            f"displaces {displaces}; ({event.ticket_id})"
        )
    return cells


def _claim_release_cells(
    event: ModelWorkClaimReleased, index: Mapping[uuid.UUID, ModelWorkEvent]
) -> list[str]:
    claim = _resolve(index, event.claim_event_id, "claim_event_id")
    if not isinstance(claim, ModelWorkClaimRequested):
        raise WorkLedgerRenderError(
            f"claim_event_id {event.claim_event_id} names a {claim.kind.value}, "
            "not a work.claim.requested"
        )
    return [
        f"re={_stamp(claim.emitted_at)}",
        f"ticket={event.ticket_id}",
        f"re-event={event.claim_event_id}",
    ]


def _hold_cells(event: ModelWorkHoldPlaced, stamp: str, lane: str) -> list[str]:
    scope = event.scope
    cells = [f"id={stamp}-{lane}"]
    addressed = event.addressed_to
    to_lanes = set(scope.lanes) | (set(addressed.lanes) if addressed else set())
    to_all = scope.all_repos or (addressed is not None and addressed.all_lanes)
    to_operator = addressed is not None and addressed.operator
    parts = _to_parts(to_lanes, to_all, to_operator)
    if parts:
        cells.append(f"to={parts}")
    if scope.repos:
        cells.append(f"repo={','.join(sorted(scope.repos))}")
    if scope.prs:
        cells.append(f"pr={_pr_keys(scope.prs)}")
    if scope.surfaces:
        if event.expires_at is None:
            raise WorkLedgerRenderError(
                "a hold on a surface renders until=<expires_at>, and this hold has no "
                "expires_at"
            )
        cells.append(f"surface={','.join(sorted(scope.surfaces))}")
        cells.append(f"until={_stamp(event.expires_at)}")
    cells.extend(_ticket(event.ticket_id))
    cells.append(f"blocks={','.join(sorted(block.value for block in event.blocks))}")
    cells.append(f"runtime-only={'yes' if event.runtime_only else 'no'}")
    cells.append(f"scope={_scope_text(scope)}")
    if event.until_text is not None and event.until_text.strip():
        cells.append(f"until-text={_text(event.until_text)}")
    return cells


def _hold_release_cells(
    event: ModelWorkHoldReleased, index: Mapping[uuid.UUID, ModelWorkEvent]
) -> list[str]:
    hold = _resolve(index, event.releases, "releases")
    if not isinstance(hold, ModelWorkHoldPlaced):
        raise WorkLedgerRenderError(
            f"releases {event.releases} names a {hold.kind.value}, not a "
            "work.hold.placed"
        )
    cells = [f"re={_row_id(hold)}"]
    cells.extend(_ticket(event.ticket_id))
    if event.partial_scope is not None:
        cells.append(f"partial={_scope_text(event.partial_scope)}")
    if hold.scope.surfaces:
        if event.surface_result is None or event.surface_restored is None:
            raise WorkLedgerRenderError(
                f"a release of the surface hold {hold.event_id} renders result= and "
                "restored=, and this release records no surface_result"
            )
        cells.append(f"surface={','.join(sorted(hold.scope.surfaces))}")
    if event.surface_result is not None:
        cells.append(f"result={event.surface_result.value.upper()}")
    if event.surface_restored is not None:
        cells.append(f"restored={'yes' if event.surface_restored else 'no'}")
    if event.reap:
        cells.append("reap=yes")
    cells.append(f"re-event={event.releases}")
    return cells


def _message_cells(
    event: ModelWorkMessageSent,
    stamp: str,
    lane: str,
    index: Mapping[uuid.UUID, ModelWorkEvent],
) -> list[str]:
    to = event.to
    cells = [
        f"to={_to_parts(set(to.lanes), to.all_lanes, to.operator)}",
        f"id={stamp}-{lane}",
    ]
    cells.extend(_ticket(event.ticket_id))
    if event.re is not None:
        target = _resolve(index, event.re, "re")
        cells.append(f"re={_row_ref(target)}")
        cells.append(f"re-event={event.re}")
    return cells


def _ack_cells(
    event: ModelWorkMessageAcked,
    stamp: str,
    lane: str,
    index: Mapping[uuid.UUID, ModelWorkEvent],
) -> list[str]:
    target = _resolve(index, event.re, "re")
    if not isinstance(
        target, ModelWorkMessageSent | ModelWorkHoldPlaced | ModelWorkRulingRecorded
    ):
        raise WorkLedgerRenderError(
            f"re {event.re} names a {target.kind.value}; an ACK acknowledges a "
            "message, a hold or a ruling"
        )
    cells = [
        f"to={_lane(target.actor)}",
        f"id={stamp}-{lane}",
        f"re={_row_ref(target)}",
    ]
    cells.extend(_ticket(event.ticket_id))
    cells.append(f"re-event={event.re}")
    return cells


def _status_cells(event: ModelWorkStatusRecorded) -> list[str]:
    cells = _ticket(event.ticket_id)
    cells.extend(_pr_ref_cells("pr", event.pr_refs))
    if event.countersigns is not None:
        cells.append(f"countersigns={event.countersigns}")
    if event.verdict is not None:
        cells.append(f"verdict={_text(event.verdict)}")
    return cells


def _result_cells(
    event: ModelWorkResultRecorded, index: Mapping[uuid.UUID, ModelWorkEvent]
) -> list[str]:
    cells = _ticket(event.ticket_id)
    cells.append(f"outcome={event.outcome.value}")
    if event.closes_claims:
        stamps: list[str] = []
        for claim_id in sorted(event.closes_claims, key=str):
            claim = _resolve(index, claim_id, "closes_claims")
            if not isinstance(claim, ModelWorkClaimRequested):
                raise WorkLedgerRenderError(
                    f"closes_claims names {claim_id}, a {claim.kind.value}, not a "
                    "work.claim.requested"
                )
            stamps.append(_stamp(claim.emitted_at))
        cells.append(f"closes-CLAIM={','.join(stamps)}")
        cells.append(f"closes-events={_ids(event.closes_claims)}")
    cells.extend(_pr_ref_cells("pr", event.pr_refs))
    cells.extend(_pr_ref_cells("occ", event.occ_refs))
    if event.friction_none:
        cells.append("friction=none")
    else:
        cells.append(f"friction=events:{_ids(event.friction_refs)}")
    return cells


def _friction_cells(event: ModelWorkFrictionRecorded) -> list[str]:
    return [
        f"ticket={event.ticket_id}",
        f"cost={_decimal(event.cost_lane_hours)} lane-hours {event.cost_basis.value}",
    ]


def _correction_cells(event: ModelWorkCorrectionRecorded) -> list[str]:
    if event.corrects is None and event.corrects_legacy_ts is None:
        raise WorkLedgerRenderError(
            "a CORRECTION row names what it corrects, and this correction sets "
            "neither corrects nor corrects_legacy_ts"
        )
    cells = _ticket(event.ticket_id)
    if event.corrects is not None:
        cells.append(f"corrects={event.corrects}")
    if event.corrects_legacy_ts is not None:
        key = "corrects-legacy" if event.corrects is not None else "corrects"
        cells.append(f"{key}={_text(event.corrects_legacy_ts)}")
    return cells


def _ruling_cells(event: ModelWorkRulingRecorded) -> list[str]:
    cells = _ticket(event.ticket_id)
    if event.amends is not None:
        cells.append(f"amends={event.amends}")
    if event.supersedes is not None:
        cells.append(f"supersedes={event.supersedes}")
    cells.append(_quoted(event.operator_words))
    return cells


def _consent_cells(event: ModelWorkOperatorConsentRecorded) -> list[str]:
    cells = _ticket(event.ticket_id)
    if event.approved_by is not None:
        cells.append(f"approved_by={event.approved_by}")
    cells.append(_quoted(event.operator_words))
    cells.append(f"APPROVED SCOPE: {'; '.join(_text(s) for s in event.approved_scope)}")
    cells.append(f"OUT OF SCOPE: {'; '.join(_text(s) for s in event.out_of_scope)}")
    return cells


def _epoch_cells(event: ModelWorkLedgerEpochOpened) -> list[str]:
    cells = [
        f"reason={event.reason}",
        f"epoch-seq={event.epoch_seq}",
        f"archived={_text(event.archived_path)}",
        f"archived-sha256={event.archived_sha256}",
        f"archived-lines={event.archived_line_count}",
        f"carried={len(event.carried)}",
    ]
    if event.review_list_ref is not None:
        cells.append(f"review-list={_text(event.review_list_ref)}")
    return cells


# ------------------------------------------------------------------ helpers


def _canonical(event: ModelWorkEvent) -> str:
    return dump_work_ledger_line(
        ModelWorkLedgerRecord.model_validate(
            {"schema": WORK_LEDGER_SCHEMA, "event": event}
        )
    )


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(_STAMP_FORMAT)


def _lane(actor: ModelActor) -> str:
    """The row's lane: a session's handle, or ``node:<node_id>.<runtime lane>``.

    A node's ``actor_key`` spells the runtime lane after ``@``, which is not a
    grammar lane character, so the row spells it after a dot instead.
    """
    if isinstance(actor, ModelSessionActor):
        return _one_token(actor.session_handle)
    return _one_token(
        f"{EnumActorKind.NODE.value}:{actor.node_id}.{actor.runtime_lane.value}"
    )


def _one_token(value: str) -> str:
    if _LANE_TOKEN_RE.match(value) is None:
        raise WorkLedgerRenderError(
            f"{value!r} is not one grammar token ([A-Za-z0-9][A-Za-z0-9_.:-]*); a "
            "lane, sender or recipient must be"
        )
    return value


def _resolve(
    index: Mapping[uuid.UUID, ModelWorkEvent], event_id: uuid.UUID, field: str
) -> ModelWorkEvent:
    target = index.get(event_id)
    if target is None:
        raise WorkLedgerRenderError(
            f"{field} names event {event_id}, which is not among the events read; "
            "its row id cannot be resolved"
        )
    return target


def _row_id(event: ModelWorkEvent) -> str:
    """The grammar id of an id-bearing row: ``<stamp>-<lane>``."""
    return f"{_stamp(event.emitted_at)}-{_lane(event.actor)}"


def _row_ref(event: ModelWorkEvent) -> str:
    """How ``re=`` names a row: its id when it has one, else its timestamp."""
    if ROW_TYPE_BY_KIND[event.kind] in _ID_BEARING_TYPES:
        return _row_id(event)
    return _stamp(event.emitted_at)


def _to_parts(lanes: set[str], all_lanes: bool, operator: bool) -> str:
    parts = [_one_token(name) for name in sorted(lanes)]
    if all_lanes:
        parts.append("all")
    if operator:
        parts.append("operator")
    return ",".join(parts)


def _pr_keys(keys: Iterable[ModelPrKey]) -> str:
    return ",".join(
        f"{key.repo}#{key.number}"
        for key in sorted(keys, key=lambda k: (k.repo, k.number))
    )


def _pr_ref_cells(key: str, refs: tuple[ModelPrRef, ...]) -> list[str]:
    if not refs:
        return []
    ordered = sorted(refs, key=lambda ref: (ref.repo, ref.number))
    cells = [f"{key}={','.join(f'{_text(r.repo)}#{r.number}' for r in ordered)}"]
    merged = [
        f"{_text(r.repo)}#{r.number}@{r.merge_sha}"
        for r in ordered
        if r.state is EnumPRState.MERGED
    ]
    if merged:
        cells.append(f"merged={','.join(merged)}")
    return cells


def _scope_text(scope: ModelHoldScope) -> str:
    parts: list[str] = []
    if scope.all_repos:
        parts.append("all_repos")
    parts.extend(f"repo:{repo}" for repo in sorted(scope.repos))
    parts.extend(
        f"pr:{key.repo}#{key.number}"
        for key in sorted(scope.prs, key=lambda k: (k.repo, k.number))
    )
    parts.extend(f"surface:{_text(name)}" for name in sorted(scope.surfaces))
    parts.extend(f"lane:{_text(name)}" for name in sorted(scope.lanes))
    return ",".join(parts)


def _ticket(ticket_id: str | None) -> list[str]:
    return [] if ticket_id is None else [f"ticket={_text(ticket_id)}"]


def _ids(ids: Iterable[uuid.UUID]) -> str:
    return ",".join(sorted(str(event_id) for event_id in ids))


def _decimal(value: Decimal) -> str:
    return f"{value.normalize():f}"


def _text(value: str) -> str:
    """Free text as one cell: whitespace collapsed, ``|`` made a broken bar."""
    return " ".join(value.split()).replace("|", _CELL_BAR)


def _quoted(words: str) -> str:
    """Operator words in the grammar's quotes, verbatim where the quotes allow."""
    text = _text(words)
    if '"' not in text:
        return f'"{text}"'
    if "”" not in text:
        return f"“{text}”"
    return '"' + text.replace('"', "'") + '"'
