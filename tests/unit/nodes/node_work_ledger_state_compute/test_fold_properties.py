# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Properties of the work-ledger fold (OMN-19405, typed work ledger T4, AC3 and AC4).

- AC3, metamorphic: replacing every free-text field (``summary``,
  ``operator_words``, ``until_text``, ``scope_text``, ``displaces``,
  ``verdict``) with each vendored adversarial wording leaves every verdict
  unchanged. The wordings (``adversarial_wordings.txt``) are the prose rows the
  omni skill parsers were caught misreading in the adversarial rounds, plus the
  2026-09-23 incident rows. The fold never reads prose, so none can move it.
- AC4: the fold is invariant under any permutation and any duplication of the
  ledger's lines (Hypothesis).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omnibase_core.enums.enum_cost_basis import EnumCostBasis
from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelRecipients,
    ModelWorkCorrectionRecorded,
    ModelWorkEvent,
    ModelWorkFrictionRecorded,
    ModelWorkOperatorConsentRecorded,
    ModelWorkRulingRecorded,
    ModelWorkStatusRecorded,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelHoldInForce,
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import (
    inbox,
    is_held,
    open_claims,
    pauses_in_force,
    surface_lease,
)

from .work_ledger_events import (
    T0,
    ack,
    actor,
    claim,
    claim_release,
    eid,
    epoch,
    hold,
    line,
    message,
    pr,
    release,
    result,
)

pytestmark = pytest.mark.unit

WORDINGS = tuple(
    text
    for text in (Path(__file__).parent / "adversarial_wordings.txt")
    .read_text(encoding="utf-8")
    .splitlines()
    if text.strip()
)
FREE_TEXT_FIELDS = (
    "summary",
    "operator_words",
    "until_text",
    "scope_text",
    "displaces",
    "verdict",
)
AS_OF = T0 + timedelta(hours=1)

REPOS = ("omnibase_infra", "omnimarket", "omnibase_core")
PRS = (
    pr("omnibase_infra", 4005),
    pr("omnibase_infra", 4013),
    pr("omnimarket", 2809),
    pr("omnimarket", 2821),
    pr("omnibase_core", 12),
)
LANES = ("lane-a", "lane-b", "merge-drain-7f")
TICKETS = ("OMN-1", "OMN-2", "OMN-3")


def _scenario() -> list[ModelWorkEvent]:
    """One of every kind, with holds released in full, in part, and invalidly."""
    return [
        epoch(),
        # A fleet runtime pause, a repo pause with one PR exempted, a PR hold,
        # a lane hold and a surface lease.
        hold(eid(1), ModelHoldScope(all_repos=True), runtime_only=True),
        hold(
            eid(2),
            ModelHoldScope(repos=frozenset({"omnibase_infra"})),
            blocks=frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
            addressed_to=ModelRecipients(all_lanes=True),
            until_text="until the lab is green",
        ),
        release(eid(3), eid(2), partial=ModelHoldScope(prs=frozenset({PRS[0]}))),
        hold(eid(4), ModelHoldScope(prs=frozenset({PRS[2], PRS[4]}))),
        release(eid(5), eid(4)),  # full release
        hold(eid(6), ModelHoldScope(lanes=frozenset({"lane-b"}))),
        hold(
            eid(7),
            ModelHoldScope(surfaces=frozenset({"dogfood-105"})),
            blocks=frozenset({EnumHoldBlock.DEPLOY}),
            expires_at=T0 + timedelta(minutes=30),
        ),
        # Invalid releases: non-subset, unknown id, surface without outcome.
        release(
            eid(8), eid(2), partial=ModelHoldScope(repos=frozenset({"omnimarket"}))
        ),
        release(eid(9), eid(999)),
        release(eid(10), eid(7)),
        release(
            eid(11),
            eid(6),
            partial=ModelHoldScope(lanes=frozenset({"lane-b"})),
            surface_result=EnumSurfaceResult.PASS,
        ),
        # Claims: one open, one released, one closed by a result.
        claim(eid(20), "OMN-1", prs=frozenset({PRS[1]}), scope_text="land it"),
        claim(eid(21), "OMN-2", lane="lane-b"),
        claim(eid(22), "OMN-3", lane="lane-b"),
        claim_release(eid(23), "OMN-2", eid(21)),
        result(eid(24), frozenset({eid(22)})),
        # Messages and acks.
        message(eid(30), ModelRecipients(lanes=frozenset({"lane-b"}))),
        message(eid(31), ModelRecipients(all_lanes=True)),
        ack(eid(32), eid(31), lane="lane-a"),
        ack(eid(33), eid(2), lane="lane-b"),
        # Kinds the fold carries but never decides from.
        ModelWorkStatusRecorded(
            event_id=eid(40), emitted_at=T0, actor=actor(), summary="s", verdict="GREEN"
        ),
        ModelWorkRulingRecorded(
            event_id=eid(41),
            emitted_at=T0,
            actor=actor(),
            summary="ruling",
            operator_words="hold everything",
        ),
        ModelWorkOperatorConsentRecorded(
            event_id=eid(42),
            emitted_at=T0,
            actor=actor(),
            summary="consent",
            operator_words="go",
            approved_scope=("the lab lane",),
            out_of_scope=("prod",),
        ),
        ModelWorkCorrectionRecorded(
            event_id=eid(43),
            emitted_at=T0,
            actor=actor(),
            summary="c",
            corrects=eid(40),
        ),
        ModelWorkFrictionRecorded(
            event_id=eid(44),
            emitted_at=T0,
            actor=actor(),
            summary="f",
            ticket_id="OMN-9",
            cost_lane_hours=Decimal("0.5"),
            cost_basis=EnumCostBasis.ESTIMATED,
        ),
    ]


def _with_wording(event: ModelWorkEvent, wording: str) -> ModelWorkEvent:
    data = event.model_dump()
    for field in FREE_TEXT_FIELDS:
        if field in type(event).model_fields:
            data[field] = wording
    return type(event).model_validate(data)


def _fold(lines: list[str]) -> ModelWorkLedgerState:
    return NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=tuple(lines), as_of=AS_OF)
    )


def _ids(holds: tuple[ModelHoldInForce, ...]) -> list[str]:
    return [str(h.hold.event_id) for h in holds]


def _battery(state: ModelWorkLedgerState) -> list[tuple[object, ...]]:
    """Every verdict the queries give over the scenario's names, with citations."""
    answers: list[tuple[object, ...]] = []
    for key in PRS:
        for action in EnumHoldBlock:
            for runtime in (True, False, None):
                verdict = is_held(state, key, action, runtime)
                answers.append(
                    ("held", key, action, runtime, verdict.status, _ids(verdict.holds))
                )
    for repo in REPOS:
        for runtime in (True, False):
            verdict = pauses_in_force(state, repo, runtime)
            answers.append(
                ("pauses", repo, runtime, verdict.status, _ids(verdict.holds))
            )
    for ticket in TICKETS:
        verdict = open_claims(state, ticket_id=ticket)
        answers.append(
            (
                "claims",
                ticket,
                verdict.status,
                [str(c.event_id) for c in verdict.claims],
            )
        )
    for lane in LANES:
        verdict = inbox(state, lane)
        answers.append(
            (
                "inbox",
                lane,
                verdict.status,
                [str(m.event_id) for m in verdict.messages],
                _ids(verdict.holds),
            )
        )
        verdict = open_claims(state, lane=lane)
        answers.append(
            (
                "lane-claims",
                lane,
                verdict.status,
                [str(c.event_id) for c in verdict.claims],
            )
        )
    verdict = surface_lease(state, "dogfood-105")
    answers.append(
        (
            "surface",
            verdict.status,
            _ids(verdict.holds),
            [h.expired_unreleased for h in verdict.holds],
        )
    )
    answers.append(
        (
            "invalid",
            [(str(bad.release.event_id), bad.reason) for bad in state.invalid_releases],
        )
    )
    return answers


BASELINE_EVENTS = _scenario()
BASELINE_LINES = [line(event) for event in BASELINE_EVENTS]
BASELINE_STATE = _fold(BASELINE_LINES)
BASELINE = _battery(BASELINE_STATE)


def test_scenario_is_decidable_and_exercises_every_answer() -> None:
    """Positive control: the battery sees HELD, CLEAR, FOUND and invalid releases."""
    assert BASELINE_STATE.decidable
    statuses = {
        cell
        for answer in BASELINE
        for cell in answer
        if isinstance(cell, EnumWorkLedgerVerdictStatus)
    }
    assert statuses == {
        EnumWorkLedgerVerdictStatus.HELD,
        EnumWorkLedgerVerdictStatus.CLEAR,
        EnumWorkLedgerVerdictStatus.FOUND,
    }
    assert len(BASELINE_STATE.invalid_releases) == 3
    assert len(WORDINGS) >= 100


@pytest.mark.parametrize("wording", WORDINGS)
def test_free_text_is_inert(wording: str) -> None:
    reworded = [_with_wording(event, wording) for event in BASELINE_EVENTS]
    assert all(e.summary == wording for e in reworded)

    assert _battery(_fold([line(event) for event in reworded])) == BASELINE


def test_free_text_check_positive_control() -> None:
    """The battery does move when a typed field moves: drop the partial release."""
    without_exemption = [line(e) for e in BASELINE_EVENTS if e.event_id != eid(3)]

    assert _battery(_fold(without_exemption)) != BASELINE


def _decision_view(state: ModelWorkLedgerState) -> ModelWorkLedgerState:
    return state.model_copy(update={"line_count": 0})


@settings(max_examples=150, deadline=None)
@given(
    order=st.permutations(range(len(BASELINE_LINES))),
    duplicates=st.lists(st.integers(0, len(BASELINE_LINES) - 1), max_size=10),
)
def test_fold_is_invariant_under_permutation_and_duplication(
    order: list[int], duplicates: list[int]
) -> None:
    lines = [BASELINE_LINES[i] for i in order] + [BASELINE_LINES[i] for i in duplicates]
    state = _fold(lines)

    assert state.line_count == len(lines)
    assert _decision_view(state) == _decision_view(BASELINE_STATE)
    assert _battery(state) == BASELINE
