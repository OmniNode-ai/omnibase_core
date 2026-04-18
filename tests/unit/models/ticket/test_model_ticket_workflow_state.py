# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ``ModelTicketWorkflowState`` and its sub-models (OMN-9142)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.ticket.enum_ticket_workflow_phase import (
    EnumTicketWorkflowPhase,
)
from omnibase_core.models.ticket.model_ticket_workflow_state import (
    ModelTicketWorkflowState,
    ModelWorkflowContext,
    ModelWorkflowGate,
    ModelWorkflowQuestion,
    ModelWorkflowRequirement,
    ModelWorkflowVerification,
)


@pytest.mark.unit
class TestEnumTicketWorkflowPhase:
    """Wire-format values must match the historical handler strings."""

    def test_string_values_are_the_persisted_wire_format(self) -> None:
        assert EnumTicketWorkflowPhase.INTAKE.value == "intake"
        assert EnumTicketWorkflowPhase.RESEARCH.value == "research"
        assert EnumTicketWorkflowPhase.QUESTIONS.value == "questions"
        assert EnumTicketWorkflowPhase.SPEC.value == "spec"
        assert EnumTicketWorkflowPhase.IMPLEMENT.value == "implement"
        assert EnumTicketWorkflowPhase.REVIEW.value == "review"
        assert EnumTicketWorkflowPhase.DONE.value == "done"

    def test_is_distinct_from_canonical_implementation_value(self) -> None:
        # Canonical EnumTicketPhase uses "implementation"; workflow uses "implement".
        # Keeping them distinct is why this enum exists.
        assert EnumTicketWorkflowPhase.IMPLEMENT.value != "implementation"


@pytest.mark.unit
class TestModelTicketWorkflowStateConstruction:
    def test_defaults_are_sane(self) -> None:
        state = ModelTicketWorkflowState()
        assert state.ticket_id == ""
        assert state.phase == EnumTicketWorkflowPhase.INTAKE
        assert state.context == ModelWorkflowContext()
        assert state.questions == []
        assert state.requirements == []
        assert state.verification == []
        assert state.gates == []
        assert state.commits == []
        assert state.pr_url is None
        assert state.hardening_tickets == []

    def test_accepts_phase_as_string(self) -> None:
        state = ModelTicketWorkflowState(phase="review")
        assert state.phase == EnumTicketWorkflowPhase.REVIEW

    def test_extra_fields_forbidden(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelTicketWorkflowState(ticket_id="OMN-1", not_a_field=True)  # type: ignore[call-arg]


@pytest.mark.unit
class TestIsQuestionsComplete:
    def test_empty_questions_is_complete(self) -> None:
        assert ModelTicketWorkflowState().is_questions_complete() is True

    def test_unanswered_required_question_is_incomplete(self) -> None:
        state = ModelTicketWorkflowState(
            questions=[ModelWorkflowQuestion(id="q1", required=True, answer=None)]
        )
        assert state.is_questions_complete() is False

    def test_unanswered_optional_question_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            questions=[ModelWorkflowQuestion(id="q1", required=False, answer=None)]
        )
        assert state.is_questions_complete() is True

    def test_answered_required_question_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            questions=[ModelWorkflowQuestion(id="q1", required=True, answer="yes")]
        )
        assert state.is_questions_complete() is True

    def test_whitespace_only_answer_is_incomplete(self) -> None:
        state = ModelTicketWorkflowState(
            questions=[ModelWorkflowQuestion(id="q1", required=True, answer="   ")]
        )
        assert state.is_questions_complete() is False


@pytest.mark.unit
class TestIsSpecComplete:
    def test_empty_requirements_is_incomplete(self) -> None:
        assert ModelTicketWorkflowState().is_spec_complete() is False

    def test_requirement_without_acceptance_is_incomplete(self) -> None:
        state = ModelTicketWorkflowState(
            requirements=[ModelWorkflowRequirement(id="r1", statement="Do X")]
        )
        assert state.is_spec_complete() is False

    def test_requirement_with_acceptance_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            requirements=[
                ModelWorkflowRequirement(
                    id="r1", statement="Do X", acceptance=["X is done"]
                )
            ]
        )
        assert state.is_spec_complete() is True


@pytest.mark.unit
class TestIsVerificationComplete:
    def test_empty_verification_is_complete(self) -> None:
        assert ModelTicketWorkflowState().is_verification_complete() is True

    def test_pending_blocking_step_is_incomplete(self) -> None:
        state = ModelTicketWorkflowState(
            verification=[
                ModelWorkflowVerification(id="v1", blocking=True, status="pending")
            ]
        )
        assert state.is_verification_complete() is False

    def test_pending_non_blocking_step_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            verification=[
                ModelWorkflowVerification(id="v1", blocking=False, status="pending")
            ]
        )
        assert state.is_verification_complete() is True

    def test_passed_blocking_step_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            verification=[
                ModelWorkflowVerification(id="v1", blocking=True, status="passed")
            ]
        )
        assert state.is_verification_complete() is True

    def test_skipped_blocking_step_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            verification=[
                ModelWorkflowVerification(id="v1", blocking=True, status="skipped")
            ]
        )
        assert state.is_verification_complete() is True


@pytest.mark.unit
class TestIsGatesComplete:
    def test_empty_gates_is_complete(self) -> None:
        assert ModelTicketWorkflowState().is_gates_complete() is True

    def test_pending_required_gate_is_incomplete(self) -> None:
        state = ModelTicketWorkflowState(
            gates=[ModelWorkflowGate(id="g1", required=True, status="pending")]
        )
        assert state.is_gates_complete() is False

    def test_approved_required_gate_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            gates=[ModelWorkflowGate(id="g1", required=True, status="approved")]
        )
        assert state.is_gates_complete() is True

    def test_pending_optional_gate_is_complete(self) -> None:
        state = ModelTicketWorkflowState(
            gates=[ModelWorkflowGate(id="g1", required=False, status="pending")]
        )
        assert state.is_gates_complete() is True


@pytest.mark.unit
class TestIsDone:
    def test_not_in_done_phase_is_not_done(self) -> None:
        state = ModelTicketWorkflowState(
            phase=EnumTicketWorkflowPhase.REVIEW,
            requirements=[
                ModelWorkflowRequirement(id="r1", statement="X", acceptance=["ok"])
            ],
        )
        assert state.is_done() is False

    def test_done_phase_without_spec_is_not_done(self) -> None:
        state = ModelTicketWorkflowState(phase=EnumTicketWorkflowPhase.DONE)
        assert state.is_done() is False

    def test_done_phase_with_all_complete_is_done(self) -> None:
        state = ModelTicketWorkflowState(
            phase=EnumTicketWorkflowPhase.DONE,
            requirements=[
                ModelWorkflowRequirement(id="r1", statement="X", acceptance=["ok"])
            ],
        )
        assert state.is_done() is True


@pytest.mark.unit
class TestGateFieldStrongTyping:
    """Gate ``kind`` / ``status`` must reject values outside their enums."""

    def test_invalid_kind_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelWorkflowGate(id="g1", kind="not_a_kind")  # type: ignore[arg-type]

    def test_invalid_status_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelWorkflowGate(id="g1", status="banana")  # type: ignore[arg-type]

    def test_valid_enum_values_accepted(self) -> None:
        from omnibase_core.enums.ticket.enum_ticket_types import (
            EnumGateKind,
            EnumTicketStepStatus,
        )

        gate = ModelWorkflowGate(
            id="g1",
            kind=EnumGateKind.POLICY_CHECK,
            status=EnumTicketStepStatus.APPROVED,
        )
        assert gate.kind == EnumGateKind.POLICY_CHECK
        assert gate.status == EnumTicketStepStatus.APPROVED
