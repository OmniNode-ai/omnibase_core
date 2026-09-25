# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Question kinds, the answer link and typed withdrawal (OMN-19620, plan T17).

Covers the model half of OMN-19620:

- AC1: a withdrawal whose actor is a human identity, that names no evidence, or
  whose reason is DUPLICATE with no event or ledger-row reference, is refused.
- AC2: a withdrawal has no answer-shaped or consent-shaped field, so it can
  never be read as an answer or as consent.

Plus the value types it rests on (``ModelLedgerRowRef``, ``ModelEvidenceRefs``),
the ``answers`` link on rulings and consents, and the partition map.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_question_withdrawal_reason import (
    EnumQuestionWithdrawalReason,
)
from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelEvidenceRefs,
    ModelLedgerRowRef,
    ModelNodeActor,
    ModelPrKey,
    ModelSessionActor,
    ModelWorkOperatorConsentRecorded,
    ModelWorkQuestionAsked,
    ModelWorkQuestionWithdrawn,
    ModelWorkRulingRecorded,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

_AT = datetime(2026, 9, 25, 15, 40, tzinfo=UTC)
_Q = uuid.UUID("11111111-1111-4111-8111-111111111111")
_W = uuid.UUID("22222222-2222-4222-8222-222222222222")
_R = uuid.UUID("33333333-3333-4333-8333-333333333333")

_ROW = {
    "path": "docs/tracking/archive/ROLLING_WORK_LEDGER_2026-09-20-split.md",
    "line": 716,
    "stamp": datetime(2026, 9, 17, 16, 24, 55, tzinfo=UTC),
    "lane": "m4-stalled-carriers-triage-1552",
}


def _lane(handle: str = "typed-withdrawal") -> ModelSessionActor:
    return ModelSessionActor(session_handle=handle, agent_kind="build-lane")


def _evidence(**fields: object) -> ModelEvidenceRefs:
    return ModelEvidenceRefs.model_validate(fields)


def _withdrawal(**overrides: object) -> ModelWorkQuestionWithdrawn:
    kwargs: dict[str, object] = {
        "event_id": _W,
        "emitted_at": _AT,
        "actor": _lane(),
        "summary": "overtaken: the AC was re-scoped by a later ticket",
        "withdraws": _Q,
        "reason": EnumQuestionWithdrawalReason.OVERTAKEN,
        "evidence": _evidence(tickets=frozenset({"OMN-17389"})),
    }
    kwargs.update(overrides)
    return ModelWorkQuestionWithdrawn.model_validate(kwargs)


def _question(**overrides: object) -> ModelWorkQuestionAsked:
    kwargs: dict[str, object] = {
        "event_id": _Q,
        "emitted_at": _AT,
        "actor": _lane("m4-stalled-carriers-triage-1552"),
        "summary": "re-issued legacy question",
        "question": "Re-scope AC2, or hold the ticket?",
        "recommendation": "re-scope",
        "legacy_row": ModelLedgerRowRef.model_validate(_ROW),
    }
    kwargs.update(overrides)
    return ModelWorkQuestionAsked.model_validate(kwargs)


# ---------------------------------------------------------------------------
# Kinds and partition
# ---------------------------------------------------------------------------


def test_question_kind_values() -> None:
    assert EnumWorkEventKind.QUESTION_ASKED.value == "work.question.asked"
    assert EnumWorkEventKind.QUESTION_WITHDRAWN.value == "work.question.withdrawn"
    assert _question().kind is EnumWorkEventKind.QUESTION_ASKED
    assert _withdrawal().kind is EnumWorkEventKind.QUESTION_WITHDRAWN


def test_question_kinds_partition_on_the_actor() -> None:
    for kind in (
        EnumWorkEventKind.QUESTION_ASKED,
        EnumWorkEventKind.QUESTION_WITHDRAWN,
    ):
        assert WORK_EVENT_PARTITION_KEY_FIELDS[kind] == "actor_key"


# ---------------------------------------------------------------------------
# ModelLedgerRowRef
# ---------------------------------------------------------------------------


def test_row_ref_accepts_a_repo_relative_md_path() -> None:
    ref = ModelLedgerRowRef.model_validate(_ROW)
    assert ref.line == 716
    assert ref.lane == "m4-stalled-carriers-triage-1552"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("path", "/abs/docs/tracking/ROLLING_WORK_LEDGER.md"),
        ("path", "docs/../tracking/ROLLING_WORK_LEDGER.md"),
        ("path", "docs/tracking/ROLLING_WORK_LEDGER.jsonl"),
        ("path", ""),
        ("line", 0),
        ("lane", "has space"),
        ("lane", ""),
        ("stamp", datetime(2026, 9, 17, 16, 24, 55)),  # naive
    ],
)
def test_row_ref_refuses_malformed_fields(field: str, value: object) -> None:
    data = dict(_ROW)
    data[field] = value
    with pytest.raises(ValidationError):
        ModelLedgerRowRef.model_validate(data)


def test_row_ref_is_hashable_and_equal_by_value() -> None:
    a = ModelLedgerRowRef.model_validate(_ROW)
    b = ModelLedgerRowRef.model_validate(dict(_ROW))
    assert a == b
    assert len({a, b}) == 1


# ---------------------------------------------------------------------------
# ModelEvidenceRefs
# ---------------------------------------------------------------------------


def test_evidence_refuses_a_value_that_names_nothing() -> None:
    with pytest.raises(ValidationError, match="names no evidence"):
        _evidence()


@pytest.mark.parametrize("ticket", ["OMN-", "omn 12", "JIRA-12", "OMN-12x", ""])
def test_evidence_refuses_a_malformed_ticket(ticket: str) -> None:
    with pytest.raises(ValidationError):
        _evidence(tickets=frozenset({ticket}))


def test_evidence_upper_cases_tickets() -> None:
    refs = _evidence(tickets=frozenset({"omn-17389"}))
    assert refs.tickets == frozenset({"OMN-17389"})


def test_evidence_accepts_each_kind_of_ref_alone() -> None:
    _evidence(prs=frozenset({ModelPrKey(repo="omninode_infra", number=1537)}))
    _evidence(events=frozenset({_R}))
    _evidence(ledger_rows=frozenset({ModelLedgerRowRef.model_validate(_ROW)}))


# ---------------------------------------------------------------------------
# work.question.asked
# ---------------------------------------------------------------------------


def test_question_without_a_legacy_row_is_valid() -> None:
    assert _question(legacy_row=None).legacy_row is None


def test_question_refuses_blank_question_text() -> None:
    with pytest.raises(ValidationError):
        _question(question="   ")


def test_question_refuses_blank_recommendation() -> None:
    with pytest.raises(ValidationError):
        _question(recommendation="  ")


# ---------------------------------------------------------------------------
# AC1 — work.question.withdrawn refusals
# ---------------------------------------------------------------------------


def test_withdrawal_by_a_lane_is_valid() -> None:
    withdrawal = _withdrawal()
    assert withdrawal.withdraws == _Q
    assert withdrawal.reason is EnumQuestionWithdrawalReason.OVERTAKEN


def test_withdrawal_by_a_node_is_valid() -> None:
    node = ModelNodeActor(
        node_id="node_ledger_reconcile",
        runtime_lane=EnumRuntimeLane.DEV,
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        run_id=uuid.UUID("44444444-4444-4444-8444-444444444444"),
    )
    assert _withdrawal(actor=node).actor == node


@pytest.mark.parametrize("handle", ["operator", "Operator", "OPERATOR", "jake", "Jake"])
def test_withdrawal_by_a_human_identity_is_refused(handle: str) -> None:
    with pytest.raises(ValidationError, match="never withdrawn by"):
        _withdrawal(actor=_lane(handle))


def test_withdrawal_with_no_evidence_is_refused() -> None:
    with pytest.raises(ValidationError):
        _withdrawal(evidence={})


def test_duplicate_withdrawal_needs_the_question_it_duplicates() -> None:
    with pytest.raises(ValidationError, match="DUPLICATE"):
        _withdrawal(
            reason=EnumQuestionWithdrawalReason.DUPLICATE,
            evidence=_evidence(tickets=frozenset({"OMN-17389"})),
        )


@pytest.mark.parametrize(
    "evidence",
    [
        {"events": frozenset({_R})},
        {"ledger_rows": frozenset({ModelLedgerRowRef.model_validate(_ROW)})},
    ],
)
def test_duplicate_withdrawal_naming_an_event_or_row_is_valid(
    evidence: dict[str, object],
) -> None:
    withdrawal = _withdrawal(
        reason=EnumQuestionWithdrawalReason.DUPLICATE, evidence=_evidence(**evidence)
    )
    assert withdrawal.reason is EnumQuestionWithdrawalReason.DUPLICATE


def test_withdrawal_cannot_withdraw_itself() -> None:
    with pytest.raises(ValidationError, match="itself"):
        _withdrawal(withdraws=_W)


def test_withdrawal_reason_values() -> None:
    assert {reason.value for reason in EnumQuestionWithdrawalReason} == {
        "overtaken",
        "duplicate",
        "premise_false",
    }


# ---------------------------------------------------------------------------
# AC2 — a withdrawal is never an answer and never consent
# ---------------------------------------------------------------------------


def test_withdrawal_has_no_answer_fields() -> None:
    forbidden = {
        "answers",
        "operator_words",
        "approved_by",
        "approved_scope",
        "out_of_scope",
    }
    assert forbidden.isdisjoint(ModelWorkQuestionWithdrawn.model_fields)


def test_no_answer_fields_can_be_smuggled_in() -> None:
    with pytest.raises(ValidationError):
        _withdrawal(answers=frozenset({_Q}))


# ---------------------------------------------------------------------------
# The answer link on rulings and consents
# ---------------------------------------------------------------------------


def _ruling(**overrides: object) -> ModelWorkRulingRecorded:
    kwargs: dict[str, object] = {
        "event_id": _R,
        "emitted_at": _AT,
        "actor": _lane("merge-drain-83"),
        "summary": "ruling",
        "operator_words": "re-scope it",
    }
    kwargs.update(overrides)
    return ModelWorkRulingRecorded.model_validate(kwargs)


def test_ruling_answers_defaults_to_nothing() -> None:
    assert _ruling().answers == frozenset()


def test_ruling_names_the_questions_it_answers() -> None:
    assert _ruling(answers=frozenset({_Q})).answers == frozenset({_Q})


def test_ruling_cannot_answer_itself() -> None:
    with pytest.raises(ValidationError, match="itself"):
        _ruling(answers=frozenset({_R}))


def test_consent_names_the_questions_it_answers() -> None:
    consent = ModelWorkOperatorConsentRecorded(
        event_id=_R,
        emitted_at=_AT,
        actor=_lane("merge-drain-83"),
        summary="consent",
        operator_words="yes",
        approved_scope=("re-install the plugin",),
        out_of_scope=("prod",),
        answers=frozenset({_Q}),
    )
    assert consent.answers == frozenset({_Q})
    data = consent.model_dump()
    data["answers"] = frozenset({_R})
    with pytest.raises(ValidationError, match="itself"):
        ModelWorkOperatorConsentRecorded.model_validate(data)
