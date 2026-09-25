# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Question status in the work-ledger fold (OMN-19620, typed work ledger T17).

- AC3: OPEN for an unanswered question; ANSWERED when a ruling or consent names
  it in ``answers``; WITHDRAWN when only a valid withdrawal names it; ANSWERED
  when both do. An answer or withdrawal naming an unknown id or a non-question
  answers or withdraws nothing and is listed.
- AC4: question status does not depend on line order or duplication, and no
  free-text field can move it.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omnibase_core.enums.enum_invalid_question_ref_reason import (
    EnumInvalidQuestionRefReason,
)
from omnibase_core.enums.enum_question_status import EnumQuestionStatus
from omnibase_core.enums.enum_question_withdrawal_reason import (
    EnumQuestionWithdrawalReason,
)
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import (
    ModelEvidenceRefs,
    ModelHoldScope,
    ModelWorkEvent,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
)
from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    fold_work_events,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import (
    health,
    questions,
)

from .work_ledger_events import (
    consent,
    eid,
    epoch,
    hold,
    line,
    question,
    ruling,
    withdrawal,
)

pytestmark = pytest.mark.unit

_OPEN = EnumQuestionStatus.OPEN
_ANSWERED = EnumQuestionStatus.ANSWERED
_WITHDRAWN = EnumQuestionStatus.WITHDRAWN

WORDINGS = tuple(
    text
    for text in (Path(__file__).parent / "adversarial_wordings.txt")
    .read_text(encoding="utf-8")
    .splitlines()
    if text.strip()
)


def _fold(*events: ModelWorkEvent) -> ModelWorkLedgerState:
    return fold_work_events([epoch(), *events])


def _status(state: ModelWorkLedgerState, question_id: uuid.UUID) -> EnumQuestionStatus:
    (match,) = [q for q in state.questions if q.question.event_id == question_id]
    return match.status


# ---------------------------------------------------------------------------
# AC3 — the three statuses and their precedence
# ---------------------------------------------------------------------------


def test_unanswered_question_is_open() -> None:
    assert _status(_fold(question(eid(1))), eid(1)) is _OPEN


def test_ruling_naming_the_question_answers_it() -> None:
    state = _fold(question(eid(1)), ruling(eid(2), answers=frozenset({eid(1)})))
    assert _status(state, eid(1)) is _ANSWERED
    (entry,) = state.questions
    assert [a.event_id for a in entry.answered_by] == [eid(2)]


def test_consent_naming_the_question_answers_it() -> None:
    state = _fold(question(eid(1)), consent(eid(2), answers=frozenset({eid(1)})))
    assert _status(state, eid(1)) is _ANSWERED


def test_ruling_that_names_nothing_answers_nothing() -> None:
    assert _status(_fold(question(eid(1)), ruling(eid(2))), eid(1)) is _OPEN


def test_withdrawal_withdraws_the_question() -> None:
    state = _fold(question(eid(1)), withdrawal(eid(2), eid(1)))
    assert _status(state, eid(1)) is _WITHDRAWN
    (entry,) = state.questions
    assert [w.event_id for w in entry.withdrawn_by] == [eid(2)]
    assert entry.answered_by == ()


def test_answer_outranks_withdrawal_and_both_are_kept() -> None:
    state = _fold(
        question(eid(1)),
        withdrawal(eid(2), eid(1)),
        ruling(eid(3), answers=frozenset({eid(1)})),
    )
    assert _status(state, eid(1)) is _ANSWERED
    (entry,) = state.questions
    assert [a.event_id for a in entry.answered_by] == [eid(3)]
    assert [w.event_id for w in entry.withdrawn_by] == [eid(2)]


def test_one_ruling_may_answer_several_questions() -> None:
    state = _fold(
        question(eid(1)),
        question(eid(2)),
        question(eid(3)),
        ruling(eid(4), answers=frozenset({eid(1), eid(2)})),
    )
    assert [_status(state, eid(n)) for n in (1, 2, 3)] == [_ANSWERED, _ANSWERED, _OPEN]


@pytest.mark.parametrize(
    "reason",
    list(EnumQuestionWithdrawalReason),
)
def test_every_reason_withdraws(reason: EnumQuestionWithdrawalReason) -> None:
    evidence = ModelEvidenceRefs(events=frozenset({eid(9)}))
    state = _fold(
        question(eid(1)), withdrawal(eid(2), eid(1), reason=reason, evidence=evidence)
    )
    assert _status(state, eid(1)) is _WITHDRAWN


def test_withdrawal_naming_an_unknown_id_is_listed_and_changes_nothing() -> None:
    state = _fold(question(eid(1)), withdrawal(eid(2), eid(99)))
    assert _status(state, eid(1)) is _OPEN
    (invalid,) = state.invalid_question_refs
    assert invalid.referrer.event_id == eid(2)
    assert invalid.target == eid(99)
    assert invalid.reason is EnumInvalidQuestionRefReason.UNKNOWN_QUESTION


def test_withdrawal_naming_a_non_question_is_listed() -> None:
    placed = hold(eid(5), ModelHoldScope(repos=frozenset({"omnibase_core"})))
    state = _fold(placed, withdrawal(eid(2), eid(5)))
    (invalid,) = state.invalid_question_refs
    assert invalid.reason is EnumInvalidQuestionRefReason.NOT_A_QUESTION
    assert state.questions == ()


def test_answer_naming_a_non_question_is_listed_and_answers_nothing() -> None:
    state = _fold(
        question(eid(1)),
        ruling(eid(2)),
        ruling(eid(3), answers=frozenset({eid(2), eid(98)})),
    )
    assert _status(state, eid(1)) is _OPEN
    reasons = {(i.target, i.reason) for i in state.invalid_question_refs}
    assert reasons == {
        (eid(2), EnumInvalidQuestionRefReason.NOT_A_QUESTION),
        (eid(98), EnumInvalidQuestionRefReason.UNKNOWN_QUESTION),
    }


def test_questions_are_sorted_by_event_id() -> None:
    state = _fold(question(eid(3)), question(eid(1)), question(eid(2)))
    assert [q.question.event_id for q in state.questions] == [eid(1), eid(2), eid(3)]


def test_health_counts_invalid_question_refs() -> None:
    state = _fold(question(eid(1)), withdrawal(eid(2), eid(99)))
    report = health(state)
    assert report.invalid_question_ref_count == 1
    assert report.open_question_count == 1


def test_handler_folds_question_lines() -> None:
    lines = tuple(
        line(event) for event in (epoch(), question(eid(1)), withdrawal(eid(2), eid(1)))
    )
    state = NodeWorkLedgerStateCompute().handle(ModelWorkLedgerFoldInput(lines=lines))
    assert _status(state, eid(1)) is _WITHDRAWN


# ---------------------------------------------------------------------------
# The questions query
# ---------------------------------------------------------------------------


def _scenario() -> ModelWorkLedgerState:
    return _fold(
        question(eid(1), ticket_id="OMN-17389"),
        question(eid(2), ticket_id="OMN-18621"),
        question(eid(3)),
        withdrawal(eid(4), eid(2)),
        ruling(eid(5), answers=frozenset({eid(3)})),
    )


def test_query_defaults_to_open_questions() -> None:
    verdict = questions(_scenario())
    assert verdict.status is EnumWorkLedgerVerdictStatus.FOUND
    assert verdict.exit_code == 3
    assert [q.question.event_id for q in verdict.questions] == [eid(1)]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (EnumQuestionStatus.OPEN, [1]),
        (EnumQuestionStatus.WITHDRAWN, [2]),
        (EnumQuestionStatus.ANSWERED, [3]),
        (None, [1, 2, 3]),
    ],
)
def test_query_filters_by_status(
    status: EnumQuestionStatus | None, expected: list[int]
) -> None:
    verdict = questions(_scenario(), status=status)
    assert [q.question.event_id for q in verdict.questions] == [
        eid(n) for n in expected
    ]


def test_query_filters_by_ticket_case_insensitively() -> None:
    verdict = questions(_scenario(), status=None, ticket_id="omn-18621")
    assert [q.question.event_id for q in verdict.questions] == [eid(2)]


def test_query_with_no_match_is_clear() -> None:
    verdict = questions(_fold(question(eid(1)), withdrawal(eid(2), eid(1))))
    assert verdict.status is EnumWorkLedgerVerdictStatus.CLEAR
    assert verdict.exit_code == 0


def test_query_without_an_epoch_is_undecided_never_clear() -> None:
    state = fold_work_events([question(eid(1))])
    verdict = questions(state)
    assert verdict.status is EnumWorkLedgerVerdictStatus.UNDECIDED
    assert verdict.exit_code == 2
    assert verdict.questions == ()


# ---------------------------------------------------------------------------
# AC4 — order, duplication and free text do not move question status
# ---------------------------------------------------------------------------


def _statuses(state: ModelWorkLedgerState) -> dict[uuid.UUID, EnumQuestionStatus]:
    return {q.question.event_id: q.status for q in state.questions}


_EVENTS: tuple[ModelWorkEvent, ...] = (
    epoch(),
    question(eid(1)),
    question(eid(2)),
    question(eid(3)),
    withdrawal(eid(4), eid(2)),
    withdrawal(eid(5), eid(3)),
    ruling(eid(6), answers=frozenset({eid(3)})),
    withdrawal(eid(7), eid(99)),
)


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_question_status_is_invariant_under_permutation_and_duplication(
    data: st.DataObject,
) -> None:
    baseline = fold_work_events(_EVENTS)
    extra = data.draw(st.lists(st.sampled_from(_EVENTS), max_size=6))
    shuffled = data.draw(st.permutations([*_EVENTS, *extra]))
    state = fold_work_events(shuffled)
    assert _statuses(state) == _statuses(baseline)
    assert state.questions == baseline.questions
    assert state.invalid_question_refs == baseline.invalid_question_refs


@pytest.mark.parametrize("wording", WORDINGS[:40])
def test_free_text_is_inert_for_questions(wording: str) -> None:
    baseline = _statuses(fold_work_events(_EVENTS))
    reworded = [
        event.model_copy(
            update={
                "summary": wording,
                **(
                    {"question": wording, "recommendation": wording}
                    if hasattr(event, "question")
                    else {}
                ),
                **(
                    {"operator_words": wording}
                    if hasattr(event, "operator_words")
                    else {}
                ),
            }
        )
        for event in _EVENTS
    ]
    assert _statuses(fold_work_events(reworded)) == baseline


def test_free_text_check_positive_control() -> None:
    """Changing a typed field does move the status, so the inertness test can fail."""
    baseline = _statuses(fold_work_events(_EVENTS))
    moved = [
        event.model_copy(update={"withdraws": eid(1)})
        if event.event_id == eid(7)
        else event
        for event in _EVENTS
    ]
    assert _statuses(fold_work_events(moved)) != baseline
