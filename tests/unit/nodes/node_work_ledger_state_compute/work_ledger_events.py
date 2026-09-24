# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed work-event builders shared by the fold tests (OMN-19405, plan T4).

Every builder takes an explicit ``event_id`` so a test names each event and can
cite it in an assertion. Timestamps default to one fixed instant; the fold does
not depend on them, and the permutation property relies on that.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.models.events.work import (
    WORK_LEDGER_SCHEMA,
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkClaimReleased,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkHoldPlaced,
    ModelWorkHoldReleased,
    ModelWorkLedgerEpochOpened,
    ModelWorkLedgerRecord,
    ModelWorkMessageAcked,
    ModelWorkMessageSent,
    ModelWorkResultRecorded,
    dump_work_ledger_line,
)

T0 = datetime(2026, 9, 23, 12, 0, 0, tzinfo=UTC)
EPOCH_ID = uuid.UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")


def eid(n: int) -> uuid.UUID:
    """A readable, deterministic event id."""
    return uuid.UUID(f"00000000-0000-4000-8000-{n:012d}")


def actor(lane: str = "lane-a") -> ModelSessionActor:
    return ModelSessionActor(session_handle=lane, agent_kind="build-lane")


def pr(repo: str, number: int) -> ModelPrKey:
    return ModelPrKey(repo=repo, number=number)


def epoch(event_id: uuid.UUID = EPOCH_ID, seq: int = 0) -> ModelWorkLedgerEpochOpened:
    return ModelWorkLedgerEpochOpened(
        event_id=event_id,
        emitted_at=T0,
        actor=actor("ledger-tool"),
        summary="cutover epoch",
        reason="cutover",
        epoch_seq=seq,
        archived_path="docs/tracking/archive/ROLLING_WORK_LEDGER_PRE_TYPED.md",
        archived_sha256="0" * 64,
        archived_line_count=10,
        review_list_ref="beta/tracking/typed-ledger-cutover-review.md",
    )


def hold(
    event_id: uuid.UUID,
    scope: ModelHoldScope,
    *,
    blocks: frozenset[EnumHoldBlock] = frozenset({EnumHoldBlock.MERGE}),
    runtime_only: bool = False,
    addressed_to: ModelRecipients | None = None,
    expires_at: datetime | None = None,
    lane: str = "lane-a",
    summary: str = "hold",
    until_text: str | None = None,
    emitted_at: datetime = T0,
) -> ModelWorkHoldPlaced:
    return ModelWorkHoldPlaced(
        event_id=event_id,
        emitted_at=emitted_at,
        actor=actor(lane),
        summary=summary,
        scope=scope,
        blocks=blocks,
        runtime_only=runtime_only,
        addressed_to=addressed_to,
        expires_at=expires_at,
        until_text=until_text,
    )


def release(
    event_id: uuid.UUID,
    releases: uuid.UUID,
    *,
    partial: ModelHoldScope | None = None,
    reap: bool = False,
    surface_result: EnumSurfaceResult | None = None,
    lane: str = "lane-b",
    summary: str = "release",
    emitted_at: datetime = T0,
) -> ModelWorkHoldReleased:
    return ModelWorkHoldReleased(
        event_id=event_id,
        emitted_at=emitted_at,
        actor=actor(lane),
        summary=summary,
        releases=releases,
        partial_scope=partial,
        reap=reap,
        surface_result=surface_result,
        surface_restored=None if surface_result is None else True,
    )


def claim(
    event_id: uuid.UUID,
    ticket_id: str,
    *,
    prs: frozenset[ModelPrKey] = frozenset(),
    lane: str = "lane-a",
    summary: str = "claim",
    scope_text: str | None = None,
) -> ModelWorkClaimRequested:
    return ModelWorkClaimRequested(
        event_id=event_id,
        emitted_at=T0,
        actor=actor(lane),
        summary=summary,
        ticket_id=ticket_id,
        prs=prs,
        scope_text=scope_text,
    )


def claim_release(
    event_id: uuid.UUID, ticket_id: str, claim_event_id: uuid.UUID
) -> ModelWorkClaimReleased:
    return ModelWorkClaimReleased(
        event_id=event_id,
        emitted_at=T0,
        actor=actor(),
        summary="claim released",
        ticket_id=ticket_id,
        claim_event_id=claim_event_id,
    )


def result(
    event_id: uuid.UUID, closes: frozenset[uuid.UUID], *, summary: str = "done"
) -> ModelWorkResultRecorded:
    return ModelWorkResultRecorded(
        event_id=event_id,
        emitted_at=T0,
        actor=actor(),
        summary=summary,
        outcome=EnumWorkOutcome.LANDED,
        closes_claims=closes,
        friction_none=True,
    )


def message(
    event_id: uuid.UUID,
    to: ModelRecipients,
    *,
    lane: str = "lane-a",
    summary: str = "message",
) -> ModelWorkMessageSent:
    return ModelWorkMessageSent(
        event_id=event_id, emitted_at=T0, actor=actor(lane), summary=summary, to=to
    )


def ack(event_id: uuid.UUID, re: uuid.UUID, *, lane: str) -> ModelWorkMessageAcked:
    return ModelWorkMessageAcked(
        event_id=event_id, emitted_at=T0, actor=actor(lane), summary="ack", re=re
    )


def line(event: ModelWorkEvent) -> str:
    """The canonical on-disk line of one event."""
    return dump_work_ledger_line(
        ModelWorkLedgerRecord.model_validate(
            {"schema": WORK_LEDGER_SCHEMA, "event": event}
        )
    )
