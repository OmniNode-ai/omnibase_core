# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The md renderer and ``onex-work-ledger render`` (OMN-16182, typed work ledger plan T6).

- AC1: each kind renders the row type from the plan's section 5.1 mapping, with
  ``lane=``, an ``id=<emitted_at>-<lane>`` for the id-bearing types (HOLD, MSG,
  ACK), an ``event=<uuid>`` cell and a ``src=typed`` cell. Golden rows, one per
  kind, plus the claim-release RELEASE.
- AC2: ``render --check`` exits 3 when the md holds an ``event=`` row whose id
  is absent from the JSONL, and 0 on a consistent pair.
- AC3: ``render --repair`` appends exactly the missing rendered rows, and a
  second run changes nothing (sha256 compared before and after).

The subprocess tests run the installed console script the way a skill runs it.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from omnibase_core.enums.enum_cost_basis import EnumCostBasis
from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.enums.governance.enum_pr_state import EnumPRState
from omnibase_core.errors.error_work_ledger_render import WorkLedgerRenderError
from omnibase_core.models.events.work import (
    WORK_LEDGER_SCHEMA,
    ModelHoldScope,
    ModelNodeActor,
    ModelPrKey,
    ModelPrRef,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkClaimReleased,
    ModelWorkClaimRequested,
    ModelWorkCorrectionRecorded,
    ModelWorkEvent,
    ModelWorkFrictionRecorded,
    ModelWorkHoldPlaced,
    ModelWorkHoldReleased,
    ModelWorkLedgerEpochOpened,
    ModelWorkLedgerRecord,
    ModelWorkMessageAcked,
    ModelWorkMessageSent,
    ModelWorkOperatorConsentRecorded,
    ModelWorkResultRecorded,
    ModelWorkRulingRecorded,
    ModelWorkStatusRecorded,
    dump_work_ledger_line,
)
from omnibase_core.models.events.work.model_work_ledger_render import (
    EPOCH_BANNER_ROW_TYPE,
    ROW_TYPE_BY_KIND,
    index_events,
    render_ledger_row,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_work_ledger_state_compute.runtime_work_ledger import (
    main,
)

pytestmark = pytest.mark.unit

SCRIPT = Path(sys.executable).with_name("onex-work-ledger")
EVENTS_ENV = "ONEX_WORK_LEDGER_PATH"
MD_ENV = "ONEX_LEDGER_PATH"

T0 = datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC)


def _id(n: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-4000-8000-{n:012d}")


EPOCH_ID = _id(1)
CLAIM_ID = _id(2)
CLAIM_RELEASE_ID = _id(3)
HOLD_ID = _id(4)
LEASE_ID = _id(5)
HOLD_RELEASE_ID = _id(6)
LEASE_RELEASE_ID = _id(7)
MSG_ID = _id(8)
ACK_ID = _id(9)
STATUS_ID = _id(10)
FRICTION_ID = _id(11)
RESULT_ID = _id(12)
RULING_ID = _id(13)
CORRECTION_ID = _id(14)
CONSENT_ID = _id(15)
RULING_ACK_ID = _id(16)

MERGE_SHA = (
    "7e" * 20
)  # a well-formed merge sha, built so no hex literal sits in the tree


def _actor(lane: str) -> ModelSessionActor:
    return ModelSessionActor(session_handle=lane, agent_kind="build-lane")


def _at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _epoch() -> ModelWorkLedgerEpochOpened:
    return ModelWorkLedgerEpochOpened(
        event_id=EPOCH_ID,
        emitted_at=_at(0),
        actor=_actor("ledger-tool"),
        summary="cutover epoch",
        reason="cutover",
        epoch_seq=0,
        archived_path="docs/tracking/archive/ROLLING_WORK_LEDGER_PRE_TYPED.md",
        archived_sha256="a" * 64,
        archived_line_count=4432,
        carried=(HOLD_ID,),
        review_list_ref="beta/tracking/typed-ledger-cutover-review.md",
    )


def _claim() -> ModelWorkClaimRequested:
    return ModelWorkClaimRequested(
        event_id=CLAIM_ID,
        emitted_at=_at(1),
        actor=_actor("lane-a"),
        summary="plan T6 renderer",
        ticket_id="OMN-16182",
        prs=frozenset(
            {
                ModelPrKey(repo="omnibase_core", number=1756),
                ModelPrKey(repo="omnibase_core", number=1700),
            }
        ),
        scope_text="renderer only. OUT OF SCOPE: T7",
        est_lane_hours=Decimal("2.0"),
        displaces="nothing",
        consent_ref=CONSENT_ID,
    )


def _claim_release() -> ModelWorkClaimReleased:
    return ModelWorkClaimReleased(
        event_id=CLAIM_RELEASE_ID,
        emitted_at=_at(2),
        actor=_actor("lane-a"),
        summary="giving the ticket back",
        ticket_id="OMN-16182",
        claim_event_id=CLAIM_ID,
    )


def _hold() -> ModelWorkHoldPlaced:
    return ModelWorkHoldPlaced(
        event_id=HOLD_ID,
        emitted_at=_at(3),
        actor=_actor("merge-drain-7f"),
        summary="runtime merge pause",
        ticket_id="OMN-17427",
        scope=ModelHoldScope(
            repos=frozenset({"omnimarket", "omnibase_infra"}),
            prs=frozenset({ModelPrKey(repo="omnibase_core", number=1756)}),
        ),
        blocks=frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
        runtime_only=True,
        addressed_to=ModelRecipients(lanes=frozenset({"runtime-train"})),
        until_text="until the lab | receipt reads PASS",
    )


def _lease() -> ModelWorkHoldPlaced:
    return ModelWorkHoldPlaced(
        event_id=LEASE_ID,
        emitted_at=_at(4),
        actor=_actor("lane-b"),
        summary="lease the dev runtime",
        scope=ModelHoldScope(surfaces=frozenset({"201-dev-runtime"})),
        blocks=frozenset({EnumHoldBlock.DEPLOY}),
        expires_at=_at(64),
    )


def _hold_release() -> ModelWorkHoldReleased:
    return ModelWorkHoldReleased(
        event_id=HOLD_RELEASE_ID,
        emitted_at=_at(5),
        actor=_actor("lane-c"),
        summary="omnibase_infra is clear",
        releases=HOLD_ID,
        partial_scope=ModelHoldScope(repos=frozenset({"omnibase_infra"})),
    )


def _lease_release() -> ModelWorkHoldReleased:
    return ModelWorkHoldReleased(
        event_id=LEASE_RELEASE_ID,
        emitted_at=_at(6),
        actor=_actor("lane-b"),
        summary="done on the dev runtime",
        releases=LEASE_ID,
        surface_result=EnumSurfaceResult.PASS,
        surface_restored=True,
    )


def _msg() -> ModelWorkMessageSent:
    return ModelWorkMessageSent(
        event_id=MSG_ID,
        emitted_at=_at(7),
        actor=_actor("lane-a"),
        summary="omnibase_core#1756 head abc123 needs landing",
        ticket_id="OMN-16182",
        to=ModelRecipients(lanes=frozenset({"merge-drain-7f"}), operator=True),
    )


def _ack() -> ModelWorkMessageAcked:
    return ModelWorkMessageAcked(
        event_id=ACK_ID,
        emitted_at=_at(8),
        actor=_actor("merge-drain-7f"),
        summary="taking it",
        re=MSG_ID,
    )


def _status() -> ModelWorkStatusRecorded:
    return ModelWorkStatusRecorded(
        event_id=STATUS_ID,
        emitted_at=_at(9),
        actor=_actor("lane-a"),
        summary="focused suite green\non two lines",
        ticket_id="OMN-16182",
        pr_refs=(
            ModelPrRef(
                repo="omnibase_core",
                number=1755,
                state=EnumPRState.MERGED,
                merge_sha=MERGE_SHA,
            ),
            ModelPrRef(repo="omnibase_core", number=1756, state=EnumPRState.OPEN),
        ),
        countersigns=RESULT_ID,
        verdict="GREEN",
    )


def _friction() -> ModelWorkFrictionRecorded:
    return ModelWorkFrictionRecorded(
        event_id=FRICTION_ID,
        emitted_at=_at(10),
        actor=_actor("lane-a"),
        summary="draft-era copies held BLOCKED",
        ticket_id="OMN-19210",
        cost_lane_hours=Decimal("0.60"),
        cost_basis=EnumCostBasis.MEASURED,
    )


def _result() -> ModelWorkResultRecorded:
    return ModelWorkResultRecorded(
        event_id=RESULT_ID,
        emitted_at=_at(11),
        actor=_actor("lane-a"),
        summary="T6 landed",
        ticket_id="OMN-16182",
        outcome=EnumWorkOutcome.LANDED,
        pr_refs=(
            ModelPrRef(
                repo="omnibase_core",
                number=1756,
                state=EnumPRState.MERGED,
                merge_sha=MERGE_SHA,
            ),
        ),
        closes_claims=frozenset({CLAIM_ID}),
        friction_refs=frozenset({FRICTION_ID}),
    )


def _ruling() -> ModelWorkRulingRecorded:
    return ModelWorkRulingRecorded(
        event_id=RULING_ID,
        emitted_at=_at(12),
        actor=_actor("omni-skill-fixes"),
        summary="plan decisions ruled",
        ticket_id="OMN-16176",
        operator_words="stick with your recommendations. update the plan then stop.",
        amends=_id(99),
    )


def _correction() -> ModelWorkCorrectionRecorded:
    return ModelWorkCorrectionRecorded(
        event_id=CORRECTION_ID,
        emitted_at=_at(13),
        actor=_actor("lane-a"),
        summary="the status named the wrong head",
        corrects=STATUS_ID,
        corrects_legacy_ts="2026-09-23T14:27:35Z",
    )


def _consent() -> ModelWorkOperatorConsentRecorded:
    return ModelWorkOperatorConsentRecorded(
        event_id=CONSENT_ID,
        emitted_at=_at(14),
        actor=_actor("lane-a"),
        summary="This row is the durable authorization evidence",
        ticket_id="OMN-16182",
        operator_words='go ahead, "restart it"',
        approved_by="operator",
        approved_scope=("restart the dev runtime", "read back health"),
        out_of_scope=("prod",),
    )


def _ruling_ack() -> ModelWorkMessageAcked:
    return ModelWorkMessageAcked(
        event_id=RULING_ACK_ID,
        emitted_at=_at(15),
        actor=_actor("lane-a"),
        summary="read the ruling",
        re=RULING_ID,
    )


def _all_events() -> list[ModelWorkEvent]:
    return [
        _epoch(),
        _consent(),
        _claim(),
        _claim_release(),
        _hold(),
        _lease(),
        _hold_release(),
        _lease_release(),
        _msg(),
        _ack(),
        _status(),
        _friction(),
        _result(),
        _ruling(),
        _correction(),
        _ruling_ack(),
    ]


EV = "event=00000000-0000-4000-8000-"

GOLDEN: dict[str, str] = {
    "epoch": (
        "2026-09-24T12:00:00Z | EPOCH | lane=ledger-tool | reason=cutover | epoch-seq=0"
        " | archived=docs/tracking/archive/ROLLING_WORK_LEDGER_PRE_TYPED.md"
        f" | archived-sha256={'a' * 64} | archived-lines=4432 | carried=1"
        " | review-list=beta/tracking/typed-ledger-cutover-review.md"
        f" | {EV}000000000001 | src=typed | cutover epoch"
    ),
    "claim": (
        "2026-09-24T12:01:00Z | CLAIM | lane=lane-a | actor=session:lane-a"
        " | ticket=OMN-16182 | pr=omnibase_core#1700,omnibase_core#1756"
        " | consent-event=00000000-0000-4000-8000-000000000015"
        " | scope=renderer only. OUT OF SCOPE: T7"
        " | est ~2 lane-hours; displaces nothing; (OMN-16182)"
        f" | {EV}000000000002 | src=typed | plan T6 renderer"
    ),
    "claim_release": (
        "2026-09-24T12:02:00Z | RELEASE | lane=lane-a | re=2026-09-24T12:01:00Z"
        " | ticket=OMN-16182 | re-event=00000000-0000-4000-8000-000000000002"
        f" | {EV}000000000003 | src=typed | giving the ticket back"
    ),
    "hold": (
        "2026-09-24T12:03:00Z | HOLD | lane=merge-drain-7f"
        " | id=2026-09-24T12:03:00Z-merge-drain-7f | to=runtime-train"
        " | repo=omnibase_infra,omnimarket | pr=omnibase_core#1756"
        " | ticket=OMN-17427 | blocks=arm,merge | runtime-only=yes"
        " | scope=repo:omnibase_infra,repo:omnimarket,pr:omnibase_core#1756"
        " | until-text=until the lab ¦ receipt reads PASS"
        f" | {EV}000000000004 | src=typed | runtime merge pause"
    ),
    "lease": (
        "2026-09-24T12:04:00Z | HOLD | lane=lane-b | id=2026-09-24T12:04:00Z-lane-b"
        " | surface=201-dev-runtime | until=2026-09-24T13:04:00Z"
        " | blocks=deploy | runtime-only=no | scope=surface:201-dev-runtime"
        f" | {EV}000000000005 | src=typed | lease the dev runtime"
    ),
    "hold_release": (
        "2026-09-24T12:05:00Z | RELEASE | lane=lane-c"
        " | re=2026-09-24T12:03:00Z-merge-drain-7f | partial=repo:omnibase_infra"
        " | re-event=00000000-0000-4000-8000-000000000004"
        f" | {EV}000000000006 | src=typed | omnibase_infra is clear"
    ),
    "lease_release": (
        "2026-09-24T12:06:00Z | RELEASE | lane=lane-b"
        " | re=2026-09-24T12:04:00Z-lane-b | surface=201-dev-runtime"
        " | result=PASS | restored=yes"
        " | re-event=00000000-0000-4000-8000-000000000005"
        f" | {EV}000000000007 | src=typed | done on the dev runtime"
    ),
    "msg": (
        "2026-09-24T12:07:00Z | MSG | lane=lane-a | from=lane-a"
        " | to=merge-drain-7f,operator | id=2026-09-24T12:07:00Z-lane-a"
        " | ticket=OMN-16182"
        f" | {EV}000000000008 | src=typed"
        " | omnibase_core#1756 head abc123 needs landing"
    ),
    "ack": (
        "2026-09-24T12:08:00Z | ACK | lane=merge-drain-7f | from=merge-drain-7f"
        " | to=lane-a | id=2026-09-24T12:08:00Z-merge-drain-7f"
        " | re=2026-09-24T12:07:00Z-lane-a"
        " | re-event=00000000-0000-4000-8000-000000000008"
        f" | {EV}000000000009 | src=typed | taking it"
    ),
    "status": (
        "2026-09-24T12:09:00Z | STATUS | lane=lane-a | ticket=OMN-16182"
        " | pr=omnibase_core#1755,omnibase_core#1756"
        f" | merged=omnibase_core#1755@{MERGE_SHA}"
        " | countersigns=00000000-0000-4000-8000-000000000012 | verdict=GREEN"
        f" | {EV}000000000010 | src=typed | focused suite green on two lines"
    ),
    "friction": (
        "2026-09-24T12:10:00Z | FRICTION | lane=lane-a | ticket=OMN-19210"
        " | cost=0.6 lane-hours measured"
        f" | {EV}000000000011 | src=typed | draft-era copies held BLOCKED"
    ),
    "result": (
        "2026-09-24T12:11:00Z | TERMINAL | lane=lane-a | ticket=OMN-16182"
        " | outcome=landed | closes-CLAIM=2026-09-24T12:01:00Z"
        " | closes-events=00000000-0000-4000-8000-000000000002"
        " | pr=omnibase_core#1756"
        f" | merged=omnibase_core#1756@{MERGE_SHA}"
        " | friction=events:00000000-0000-4000-8000-000000000011"
        f" | {EV}000000000012 | src=typed | T6 landed"
    ),
    "ruling": (
        "2026-09-24T12:12:00Z | RULING | lane=omni-skill-fixes | ticket=OMN-16176"
        " | amends=00000000-0000-4000-8000-000000000099"
        ' | "stick with your recommendations. update the plan then stop."'
        f" | {EV}000000000013 | src=typed | plan decisions ruled"
    ),
    "correction": (
        "2026-09-24T12:13:00Z | CORRECTION | lane=lane-a"
        " | corrects=00000000-0000-4000-8000-000000000010"
        " | corrects-legacy=2026-09-23T14:27:35Z"
        f" | {EV}000000000014 | src=typed | the status named the wrong head"
    ),
    "consent": (
        "2026-09-24T12:14:00Z | OPERATOR-CONSENT | lane=lane-a | ticket=OMN-16182"
        " | approved_by=operator"
        ' | “go ahead, "restart it"”'
        " | APPROVED SCOPE: restart the dev runtime; read back health"
        " | OUT OF SCOPE: prod"
        f" | {EV}000000000015 | src=typed"
        " | This row is the durable authorization evidence"
    ),
    "ruling_ack": (
        "2026-09-24T12:15:00Z | ACK | lane=lane-a | from=lane-a"
        " | to=omni-skill-fixes | id=2026-09-24T12:15:00Z-lane-a"
        " | re=2026-09-24T12:12:00Z"
        " | re-event=00000000-0000-4000-8000-000000000013"
        f" | {EV}000000000016 | src=typed | read the ruling"
    ),
}

FIXTURES = {
    "epoch": _epoch,
    "claim": _claim,
    "claim_release": _claim_release,
    "hold": _hold,
    "lease": _lease,
    "hold_release": _hold_release,
    "lease_release": _lease_release,
    "msg": _msg,
    "ack": _ack,
    "status": _status,
    "friction": _friction,
    "result": _result,
    "ruling": _ruling,
    "correction": _correction,
    "consent": _consent,
    "ruling_ack": _ruling_ack,
}


# --------------------------------------------------------------------------- AC1


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_golden_row_per_kind(name: str) -> None:
    index = index_events(_all_events())
    assert render_ledger_row(FIXTURES[name](), index) == GOLDEN[name]


def test_every_kind_has_a_golden_row() -> None:
    kinds = {FIXTURES[name]().kind for name in FIXTURES}
    assert kinds == set(ROW_TYPE_BY_KIND)
    assert len(ROW_TYPE_BY_KIND) == 13


def test_row_type_mapping_is_the_plan_table() -> None:
    by_value = {kind.value: row_type for kind, row_type in ROW_TYPE_BY_KIND.items()}
    assert by_value == {
        "work.claim.requested": "CLAIM",
        "work.status.recorded": "STATUS",
        "work.result.recorded": "TERMINAL",
        "work.friction.recorded": "FRICTION",
        "work.correction.recorded": "CORRECTION",
        "work.ruling.recorded": "RULING",
        "work.consent.recorded": "OPERATOR-CONSENT",
        "work.message.sent": "MSG",
        "work.message.acked": "ACK",
        "work.hold.placed": "HOLD",
        "work.hold.released": "RELEASE",
        "work.claim.released": "RELEASE",
        "work.ledger.epoch.opened": EPOCH_BANNER_ROW_TYPE,
    }


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_every_row_carries_lane_event_and_src_cells(name: str) -> None:
    event = FIXTURES[name]()
    row = render_ledger_row(event, index_events(_all_events()))
    cells = [cell.strip() for cell in row.split("|")]
    assert cells[1] == ROW_TYPE_BY_KIND[event.kind]
    assert cells[2].startswith("lane=")
    assert f"event={event.event_id}" in cells
    assert cells.index("src=typed") == cells.index(f"event={event.event_id}") + 1
    if cells[1] in {"HOLD", "MSG", "ACK"}:
        lane = cells[2].removeprefix("lane=")
        assert f"id={cells[0]}-{lane}" in cells
    else:
        assert not any(cell.startswith("id=") for cell in cells)
    assert "\n" not in row


def test_render_is_deterministic_and_ignores_index_order() -> None:
    events = _all_events()
    forward = [render_ledger_row(e, index_events(events)) for e in events]
    backward = [
        render_ledger_row(e, index_events(list(reversed(events)))) for e in events
    ]
    assert forward == backward


def test_emitted_at_renders_in_utc_to_the_second() -> None:
    offset = datetime(
        2026, 9, 24, 8, 0, 5, 999_999, tzinfo=timezone(timedelta(hours=-4))
    )
    event = _status().model_copy(update={"emitted_at": offset})
    row = render_ledger_row(event, index_events(_all_events()))
    expected = "2026-09-24T12:00:05Z"
    assert row.startswith(f"{expected} | STATUS | ")


def test_node_actor_lane_is_one_grammar_token() -> None:
    actor = ModelNodeActor(
        node_id="node_pr_lifecycle_orchestrator",
        runtime_lane=EnumRuntimeLane.STABILITY_TEST,
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        run_id=_id(500),
    )
    event = _status().model_copy(update={"actor": actor, "actor_key": actor.actor_key})
    row = render_ledger_row(event, index_events(_all_events()))
    assert " | lane=node:node_pr_lifecycle_orchestrator.stability-test | " in row


def test_fleet_wide_hold_renders_to_all() -> None:
    hold = ModelWorkHoldPlaced(
        event_id=_id(600),
        emitted_at=_at(20),
        actor=_actor("cutover"),
        summary="fleet hold for the cutover",
        scope=ModelHoldScope(all_repos=True),
        blocks=frozenset(
            {EnumHoldBlock.MERGE, EnumHoldBlock.ARM, EnumHoldBlock.DISPATCH}
        ),
    )
    row = render_ledger_row(hold, {})
    assert " | to=all | " in row
    assert " | scope=all_repos | " in row


# ----------------------------------------------------------- render refusals


def test_unresolvable_reference_is_refused() -> None:
    with pytest.raises(
        WorkLedgerRenderError, match="00000000-0000-4000-8000-000000000008"
    ):
        render_ledger_row(_ack(), {})


def test_ack_of_a_kind_that_takes_no_ack_is_refused() -> None:
    ack = _ack().model_copy(update={"re": STATUS_ID})
    with pytest.raises(WorkLedgerRenderError, match=r"work\.status\.recorded"):
        render_ledger_row(ack, index_events(_all_events()))


def test_hold_release_naming_a_claim_is_refused() -> None:
    release = _hold_release().model_copy(update={"releases": CLAIM_ID})
    with pytest.raises(WorkLedgerRenderError, match=r"not a work\.hold\.placed"):
        render_ledger_row(release, index_events(_all_events()))


def test_surface_release_without_result_is_refused() -> None:
    release = ModelWorkHoldReleased(
        event_id=_id(700),
        emitted_at=_at(30),
        actor=_actor("lane-b"),
        summary="done",
        releases=LEASE_ID,
    )
    with pytest.raises(WorkLedgerRenderError, match="result"):
        render_ledger_row(release, index_events(_all_events()))


def test_surface_hold_without_expiry_is_refused() -> None:
    lease = _lease().model_copy(update={"expires_at": None})
    with pytest.raises(WorkLedgerRenderError, match="until="):
        render_ledger_row(lease, {})


def test_correction_naming_nothing_is_refused() -> None:
    correction = _correction().model_copy(
        update={"corrects": None, "corrects_legacy_ts": None}
    )
    with pytest.raises(WorkLedgerRenderError, match="corrects"):
        render_ledger_row(correction, {})


def test_lane_that_is_not_one_token_is_refused() -> None:
    event = _status().model_copy(
        update={
            "actor": _actor("two words"),
            "actor_key": "session:two words",
        }
    )
    with pytest.raises(WorkLedgerRenderError, match="two words"):
        render_ledger_row(event, index_events(_all_events()))


def test_conflicting_duplicate_in_index_is_refused() -> None:
    other = _msg().model_copy(update={"summary": "different words"})
    with pytest.raises(WorkLedgerRenderError, match="conflicting"):
        index_events([_msg(), other])


def test_identical_duplicate_in_index_counts_once() -> None:
    assert len(index_events([_msg(), _msg()])) == 1


# ------------------------------------------------------------- AC2 and AC3 CLI


def _jsonl_line(event: ModelWorkEvent) -> str:
    return dump_work_ledger_line(
        ModelWorkLedgerRecord.model_validate(
            {"schema": WORK_LEDGER_SCHEMA, "event": event}
        )
    )


LEGACY_MD = (
    "# Rolling work ledger\n"
    "\n"
    "2026-09-23T14:27:35Z | STATUS | lane=omn17427-foreground | a legacy prose row\n"
)


def _write_pair(
    tmp_path: Path, events: list[ModelWorkEvent], md_events: list[ModelWorkEvent]
) -> tuple[Path, Path]:
    jsonl = tmp_path / "ROLLING_WORK_LEDGER.jsonl"
    jsonl.write_text("".join(_jsonl_line(e) + "\n" for e in events), encoding="utf-8")
    index = index_events(events + md_events)
    md = tmp_path / "ROLLING_WORK_LEDGER.md"
    md.write_text(
        LEGACY_MD + "".join(render_ledger_row(e, index) + "\n" for e in md_events),
        encoding="utf-8",
    )
    return jsonl, md


def _run(
    jsonl: Path | None, md: Path | None, *args: str
) -> subprocess.CompletedProcess[str]:
    assert SCRIPT.exists(), f"console script missing: {SCRIPT}"
    env = {"PATH": str(SCRIPT.parent)}
    if jsonl is not None:
        env[EVENTS_ENV] = str(jsonl)
    if md is not None:
        env[MD_ENV] = str(md)
    return subprocess.run(
        [str(SCRIPT), "render", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_check_is_clear_on_a_consistent_pair(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    proc = _run(jsonl, md, "--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "verdict=clear query=render mode=check" in proc.stdout
    assert (
        f"events={len(events)} md_rows={len(events)} md_ahead=0 md_missing=0"
        in proc.stdout
    )


def test_check_finds_an_md_row_absent_from_the_jsonl(tmp_path: Path) -> None:
    events = _all_events()
    ahead = _msg().model_copy(update={"event_id": _id(800), "emitted_at": _at(40)})
    jsonl, md = _write_pair(tmp_path, events, [*events, ahead])
    proc = _run(jsonl, md, "--check")
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "verdict=found query=render mode=check" in proc.stdout
    assert f"divergence=md-ahead event={_id(800)}" in proc.stdout
    assert "md_ahead=1 md_missing=0" in proc.stdout


def test_check_finds_a_jsonl_event_missing_from_the_md(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events[:-1])
    proc = _run(jsonl, md, "--check")
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert f"divergence=md-missing event={events[-1].event_id}" in proc.stdout
    assert "md_ahead=0 md_missing=1" in proc.stdout


def test_check_prints_both_headers(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    lines = _run(jsonl, md, "--check").stdout.splitlines()
    assert lines[0] == (
        f"ledger={jsonl} sha256={_sha(jsonl)} lines={len(events)} epoch={EPOCH_ID}"
    )
    md_lines = len(md.read_text(encoding="utf-8").splitlines())
    assert lines[1] == f"md={md} sha256={_sha(md)} lines={md_lines}"


def test_check_is_undecided_without_the_events_variable(tmp_path: Path) -> None:
    _, md = _write_pair(tmp_path, _all_events(), _all_events())
    proc = _run(None, md, "--check")
    assert proc.returncode == 2
    assert EVENTS_ENV in proc.stdout


def test_check_is_undecided_without_the_md_path(tmp_path: Path) -> None:
    jsonl, _ = _write_pair(tmp_path, _all_events(), _all_events())
    proc = _run(jsonl, None, "--check")
    assert proc.returncode == 2
    assert MD_ENV in proc.stdout


def test_md_option_overrides_the_md_variable(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    proc = _run(jsonl, tmp_path / "absent.md", "--check", "--md", str(md))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_check_is_undecided_on_an_unparseable_jsonl_line(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    with jsonl.open("a", encoding="utf-8") as handle:
        handle.write('{"schema":"onex.work-ledger/1"}\n')
    proc = _run(jsonl, md, "--check")
    assert proc.returncode == 2
    assert "reason=" in proc.stdout


def test_check_ignores_an_unterminated_jsonl_tail(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    with jsonl.open("a", encoding="utf-8") as handle:
        handle.write('{"schema":"onex.wo')
    proc = _run(jsonl, md, "--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_check_is_undecided_on_a_conflicting_duplicate_event(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    with jsonl.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(_msg().model_copy(update={"summary": "other"})) + "\n")
    proc = _run(jsonl, md, "--check")
    assert proc.returncode == 2
    assert "conflicting" in proc.stdout


def test_check_and_repair_are_mutually_exclusive_and_one_is_required(
    tmp_path: Path,
) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    assert _run(jsonl, md).returncode == 2
    assert _run(jsonl, md, "--check", "--repair").returncode == 2


def test_repair_appends_exactly_the_missing_rows_then_changes_nothing(
    tmp_path: Path,
) -> None:
    events = _all_events()
    kept = [events[0], events[2], events[4]]
    jsonl, md = _write_pair(tmp_path, events, kept)
    before = md.read_text(encoding="utf-8")
    index = index_events(events)
    missing = [e for e in events if e not in kept]

    first = _run(jsonl, md, "--repair")
    assert first.returncode == 0, first.stdout + first.stderr
    assert f"repaired={len(missing)}" in first.stdout
    after = md.read_text(encoding="utf-8")
    assert after == before + "".join(
        render_ledger_row(e, index) + "\n" for e in missing
    )

    sha_before = _sha(md)
    second = _run(jsonl, md, "--repair")
    assert second.returncode == 0, second.stdout + second.stderr
    assert "repaired=0" in second.stdout
    assert _sha(md) == sha_before

    check = _run(jsonl, md, "--check")
    assert check.returncode == 0, check.stdout + check.stderr


def test_repair_adds_a_newline_before_appending_to_an_unterminated_md(
    tmp_path: Path,
) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events[:-1])
    md.write_text(md.read_text(encoding="utf-8").removesuffix("\n"), encoding="utf-8")
    proc = _run(jsonl, md, "--repair")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    tail = md.read_text(encoding="utf-8").splitlines()[-1]
    assert tail == render_ledger_row(events[-1], index_events(events))


def test_repair_still_reports_md_ahead_and_writes_nothing_for_it(
    tmp_path: Path,
) -> None:
    events = _all_events()
    ahead = _msg().model_copy(update={"event_id": _id(801), "emitted_at": _at(41)})
    jsonl, md = _write_pair(tmp_path, events, [*events, ahead])
    sha_before = _sha(md)
    proc = _run(jsonl, md, "--repair")
    assert proc.returncode == 3
    assert f"divergence=md-ahead event={_id(801)}" in proc.stdout
    assert _sha(md) == sha_before


def test_repair_writes_nothing_when_a_missing_row_cannot_render(tmp_path: Path) -> None:
    events = [_epoch(), _ack()]  # the ack's message is not in the ledger
    jsonl, md = _write_pair(tmp_path, events, [_epoch()])
    sha_before = _sha(md)
    proc = _run(jsonl, md, "--repair")
    assert proc.returncode == 2
    assert "reason=" in proc.stdout
    assert _sha(md) == sha_before


def test_repair_takes_the_md_lock_file_beside_the_ledger(tmp_path: Path) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events[:1])
    assert _run(jsonl, md, "--repair").returncode == 0
    locks = tmp_path / ".ledger_locks"
    digest = hashlib.sha256(str(md.resolve()).encode("utf-8")).hexdigest()[:24]
    assert (locks / f"ROLLING_WORK_LEDGER.md.{digest}.flock").exists()
    assert (locks / ".gitignore").read_text(encoding="utf-8").endswith("*\n")


def test_repair_md_lock_file_is_owner_only(tmp_path: Path) -> None:
    # CodeQL py/overly-permissive-file: the lock file is created without group
    # or world permission bits, whatever the caller's umask.
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events[:1])
    assert _run(jsonl, md, "--repair").returncode == 0
    digest = hashlib.sha256(str(md.resolve()).encode("utf-8")).hexdigest()[:24]
    lock = tmp_path / ".ledger_locks" / f"ROLLING_WORK_LEDGER.md.{digest}.flock"
    assert lock.stat().st_mode & 0o077 == 0


def test_render_in_process_matches_the_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events = _all_events()
    jsonl, md = _write_pair(tmp_path, events, events)
    monkeypatch.setenv(EVENTS_ENV, str(jsonl))
    monkeypatch.setenv(MD_ENV, str(md))
    assert main(["render", "--check"]) == 0
    assert "verdict=clear query=render mode=check" in capsys.readouterr().out
