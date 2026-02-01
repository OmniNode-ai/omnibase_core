"""Comprehensive unit tests for TicketContract model (OMN-1807).

Tests cover all requirements from the ticket Definition of Done:
- R1: Enum Tests
- R2: Status Validator Tests
- R3: Research Notes Tests
- R4: Phase Enforcement Tests
- R5: Completion Check Tests
- R6: Fingerprint Tests
- R8: YAML Round-Trip Tests
"""

from __future__ import annotations

import json
import re
from datetime import datetime

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.ticket import (
    Action,
    ClarifyingQuestion,
    Gate,
    GateKind,
    Phase,
    Requirement,
    Status,
    TicketContract,
    VerificationKind,
    VerificationStep,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def basic_contract() -> TicketContract:
    """Create a minimal TicketContract for testing."""
    return TicketContract(
        ticket_id="OMN-TEST",
        title="Test Ticket",
    )


@pytest.fixture
def contract_with_questions() -> TicketContract:
    """Create a contract with clarifying questions."""
    return TicketContract(
        ticket_id="OMN-QUESTIONS",
        title="Ticket With Questions",
        phase=Phase.QUESTIONS,
        questions=[
            ClarifyingQuestion(
                id="q1",
                text="What is the scope?",
                category="scope",
                required=True,
                answer=None,
            ),
            ClarifyingQuestion(
                id="q2",
                text="What is the timeline?",
                category="timeline",
                required=True,
                answer="Two weeks",
                answered_at=datetime.now(),
            ),
            ClarifyingQuestion(
                id="q3",
                text="Any dependencies?",
                category="dependency",
                required=False,
                answer=None,
            ),
        ],
    )


@pytest.fixture
def contract_with_verification() -> TicketContract:
    """Create a contract with verification steps."""
    return TicketContract(
        ticket_id="OMN-VERIFY",
        title="Ticket With Verification",
        phase=Phase.IMPLEMENTATION,
        verification_steps=[
            VerificationStep(
                id="v1",
                kind=VerificationKind.UNIT_TESTS,
                command="pytest tests/",
                blocking=True,
                status=Status.PENDING,
            ),
            VerificationStep(
                id="v2",
                kind=VerificationKind.LINT,
                command="ruff check .",
                blocking=True,
                status=Status.PASSED,
            ),
            VerificationStep(
                id="v3",
                kind=VerificationKind.MANUAL_CHECK,
                blocking=False,
                status=Status.PENDING,
            ),
        ],
    )


@pytest.fixture
def contract_with_gates() -> TicketContract:
    """Create a contract with approval gates."""
    return TicketContract(
        ticket_id="OMN-GATES",
        title="Ticket With Gates",
        phase=Phase.REVIEW,
        gates=[
            Gate(
                id="g1",
                kind=GateKind.HUMAN_APPROVAL,
                description="Code review approval",
                required=True,
                status=Status.PENDING,
            ),
            Gate(
                id="g2",
                kind=GateKind.SECURITY_CHECK,
                description="Security review",
                required=True,
                status=Status.APPROVED,
                approver="security-team",
                decided_at=datetime.now(),
            ),
            Gate(
                id="g3",
                kind=GateKind.POLICY_CHECK,
                description="Optional policy check",
                required=False,
                status=Status.PENDING,
            ),
        ],
    )


@pytest.fixture
def complete_contract() -> TicketContract:
    """Create a contract that passes is_done()."""
    return TicketContract(
        ticket_id="OMN-COMPLETE",
        title="Complete Ticket",
        phase=Phase.DONE,
        questions=[
            ClarifyingQuestion(
                id="q1",
                text="Scope question",
                category="scope",
                required=True,
                answer="The scope is X",
                answered_at=datetime.now(),
            ),
        ],
        requirements=[
            Requirement(
                id="r1",
                statement="Implement feature X",
                rationale="Business need",
                acceptance=["Given/When/Then criteria"],
            ),
        ],
        verification_steps=[
            VerificationStep(
                id="v1",
                kind=VerificationKind.UNIT_TESTS,
                blocking=True,
                status=Status.PASSED,
            ),
        ],
        gates=[
            Gate(
                id="g1",
                kind=GateKind.HUMAN_APPROVAL,
                description="Final approval",
                required=True,
                status=Status.APPROVED,
                approver="reviewer",
                decided_at=datetime.now(),
            ),
        ],
    )


# =============================================================================
# R1: Enum Tests
# =============================================================================


@pytest.mark.unit
class TestEnumSerialization:
    """Test enum string serialization (R1)."""

    def test_enums_are_str_subclass(self):
        """Verify all enums are subclasses of str for JSON serialization."""
        assert isinstance(Phase.INTAKE, str)
        assert isinstance(Action.FETCH_TICKET, str)
        assert isinstance(Status.PENDING, str)
        assert isinstance(VerificationKind.UNIT_TESTS, str)
        assert isinstance(GateKind.HUMAN_APPROVAL, str)

    def test_enums_serialize_to_plain_strings(self):
        """Verify enums serialize to plain strings, not Python object notation."""
        contract = TicketContract(
            ticket_id="OMN-ENUM",
            title="Enum Test",
            phase=Phase.RESEARCH,
        )

        # JSON serialization
        json_data = contract.model_dump(mode="json")
        assert json_data["phase"] == "research"
        assert not str(json_data["phase"]).startswith("EnumTicketPhase")

        # YAML serialization
        yaml_output = contract.to_yaml()
        assert "!!python/object" not in yaml_output
        assert "phase: research" in yaml_output

    def test_enum_str_returns_value(self):
        """Verify str() on enums returns the value."""
        assert str(Phase.INTAKE) == "intake"
        assert str(Action.COMMIT) == "commit"
        assert str(Status.PASSED) == "passed"


# =============================================================================
# R2: Status Validator Tests
# =============================================================================


@pytest.mark.unit
class TestStatusValidation:
    """Test status validation for VerificationStep and Gate (R2)."""

    def test_verification_step_rejects_approved_status(self):
        """VerificationStep cannot have status=approved."""
        with pytest.raises(ModelOnexError) as exc_info:
            VerificationStep(
                id="v1",
                kind=VerificationKind.UNIT_TESTS,
                status=Status.APPROVED,  # Invalid for verification steps
            )

        assert "cannot have status='approved'" in str(exc_info.value)

    def test_verification_step_accepts_valid_statuses(self):
        """VerificationStep accepts pending/passed/failed/skipped."""
        valid_statuses = [Status.PENDING, Status.PASSED, Status.FAILED, Status.SKIPPED]

        for status in valid_statuses:
            step = VerificationStep(
                id=f"v_{status.value}",
                kind=VerificationKind.LINT,
                status=status,
            )
            assert step.status == status

    def test_gate_rejects_passed_status(self):
        """Gate cannot have status=passed."""
        with pytest.raises(ModelOnexError) as exc_info:
            Gate(
                id="g1",
                kind=GateKind.HUMAN_APPROVAL,
                description="Test gate",
                status=Status.PASSED,  # Invalid for gates
            )

        assert "cannot have status='passed'" in str(exc_info.value)

    def test_gate_accepts_valid_statuses(self):
        """Gate accepts pending/approved/rejected/skipped."""
        valid_statuses = [
            Status.PENDING,
            Status.APPROVED,
            Status.REJECTED,
            Status.SKIPPED,
        ]

        for status in valid_statuses:
            gate = Gate(
                id=f"g_{status.value}",
                kind=GateKind.POLICY_CHECK,
                description="Test gate",
                status=status,
            )
            assert gate.status == status

    def test_verification_step_allows_rejected_status(self):
        """VerificationStep allows rejected status (implementation choice).

        Note: The implementation only forbids 'approved' for verification steps.
        While 'rejected' is semantically unusual for verification (passed/failed
        is more typical), the implementation allows it.
        """
        # This should NOT raise - rejected is allowed
        step = VerificationStep(
            id="v1",
            kind=VerificationKind.UNIT_TESTS,
            status=Status.REJECTED,
        )
        assert step.status == Status.REJECTED

    def test_gate_allows_failed_status(self):
        """Gate allows failed status (implementation choice).

        Note: The implementation only forbids 'passed' for gates.
        While 'failed' is semantically unusual for gates (approved/rejected
        is more typical), the implementation allows it.
        """
        # This should NOT raise - failed is allowed
        gate = Gate(
            id="g1",
            kind=GateKind.HUMAN_APPROVAL,
            description="Test gate",
            status=Status.FAILED,
        )
        assert gate.status == Status.FAILED


# =============================================================================
# R3: Research Notes Tests
# =============================================================================


@pytest.mark.unit
class TestResearchNotes:
    """Test research_notes as a derived property (R3)."""

    def test_research_notes_is_property_not_field(self):
        """research_notes is a @property, not a model field."""
        contract = TicketContract(
            ticket_id="OMN-NOTES",
            title="Notes Test",
            context={"research_notes": "These are research notes"},
        )

        # Can access via property
        assert contract.research_notes == "These are research notes"

        # But it's not a field
        assert "research_notes" not in contract.model_fields

    def test_research_notes_not_in_model_dump(self):
        """research_notes should not appear in model_dump output."""
        contract = TicketContract(
            ticket_id="OMN-NOTES",
            title="Notes Test",
            context={"research_notes": "Some notes"},
        )

        dumped = contract.model_dump()

        # research_notes is in context, not at top level
        assert "research_notes" not in dumped
        # The context dict still contains it
        assert dumped["context"]["research_notes"] == "Some notes"

    def test_research_notes_derives_from_context(self):
        """research_notes is derived from context['research_notes']."""
        # String value
        contract1 = TicketContract(
            ticket_id="OMN-1",
            title="Test 1",
            context={"research_notes": "Note string"},
        )
        assert contract1.research_notes == "Note string"

        # List value gets joined
        contract2 = TicketContract(
            ticket_id="OMN-2",
            title="Test 2",
            context={"research_notes": ["Note 1", "Note 2", "Note 3"]},
        )
        assert contract2.research_notes == "Note 1\nNote 2\nNote 3"

        # Missing value returns empty string
        contract3 = TicketContract(
            ticket_id="OMN-3",
            title="Test 3",
            context={},
        )
        assert contract3.research_notes == ""

        # None value returns empty string
        contract4 = TicketContract(
            ticket_id="OMN-4",
            title="Test 4",
            context={"research_notes": None},
        )
        assert contract4.research_notes == ""


# =============================================================================
# R4: Phase Enforcement Tests
# =============================================================================


@pytest.mark.unit
class TestPhaseEnforcement:
    """Test phase-based action enforcement (R4)."""

    def test_assert_action_allowed_string_input(self, basic_contract: TicketContract):
        """assert_action_allowed accepts string 'ask_question'."""
        # Set phase to QUESTIONS where ASK_QUESTION is allowed
        basic_contract.phase = Phase.QUESTIONS

        # Should not raise - string input works
        basic_contract.assert_action_allowed("ask_question")

    def test_assert_action_allowed_enum_input(self, basic_contract: TicketContract):
        """assert_action_allowed accepts Action.ASK_QUESTION enum."""
        basic_contract.phase = Phase.QUESTIONS

        # Should not raise - enum input works
        basic_contract.assert_action_allowed(Action.ASK_QUESTION)

    def test_assert_action_not_allowed_raises(self, basic_contract: TicketContract):
        """assert_action_allowed raises ModelOnexError for wrong phase."""
        # INTAKE phase only allows FETCH_TICKET
        basic_contract.phase = Phase.INTAKE

        with pytest.raises(ModelOnexError) as exc_info:
            basic_contract.assert_action_allowed(Action.COMMIT)

        error = exc_info.value
        assert "commit" in str(error).lower()
        assert "intake" in str(error).lower()

    def test_allowed_actions_returns_frozenset_of_enums(
        self, basic_contract: TicketContract
    ):
        """allowed_actions() returns frozenset[Action] enum values."""
        basic_contract.phase = Phase.IMPLEMENTATION

        allowed = basic_contract.allowed_actions()

        assert isinstance(allowed, frozenset)
        assert len(allowed) > 0
        # All items should be Action enum values
        for action in allowed:
            assert isinstance(action, Action)

        # Check expected actions for IMPLEMENTATION phase
        assert Action.MODIFY_CODE in allowed
        assert Action.COMMIT in allowed
        assert Action.RUN_VERIFICATION in allowed

    def test_each_phase_has_defined_actions(self):
        """Verify each phase has appropriate allowed actions."""
        contract = TicketContract(ticket_id="OMN-PHASES", title="Phase Test")

        expected_actions = {
            Phase.INTAKE: {Action.FETCH_TICKET},
            Phase.RESEARCH: {Action.PARALLEL_SOLVE},
            Phase.QUESTIONS: {Action.ASK_QUESTION, Action.EDIT_REQUIREMENTS},
            Phase.SPEC: {Action.EDIT_REQUIREMENTS, Action.EDIT_VERIFICATION},
            Phase.IMPLEMENTATION: {
                Action.MODIFY_CODE,
                Action.COMMIT,
                Action.RUN_VERIFICATION,
            },
            Phase.REVIEW: {Action.RUN_VERIFICATION, Action.OPEN_HARDENING_TICKET},
            Phase.DONE: set(),
        }

        for phase, expected in expected_actions.items():
            contract.phase = phase
            assert contract.allowed_actions() == expected, f"Phase {phase} mismatch"

    def test_invalid_action_string_raises(self, basic_contract: TicketContract):
        """assert_action_allowed raises for invalid action string."""
        with pytest.raises(ModelOnexError) as exc_info:
            basic_contract.assert_action_allowed("not_a_real_action")

        assert "invalid action" in str(exc_info.value).lower()


# =============================================================================
# R5: Completion Check Tests
# =============================================================================


@pytest.mark.unit
class TestCompletionChecks:
    """Test completion check methods (R5)."""

    # --- is_questions_complete ---

    def test_is_questions_complete_empty_list(self, basic_contract: TicketContract):
        """is_questions_complete returns True when no questions exist."""
        assert basic_contract.questions == []
        assert basic_contract.is_questions_complete() is True

    def test_is_questions_complete_all_answered(self):
        """is_questions_complete returns True when all required questions answered."""
        contract = TicketContract(
            ticket_id="OMN-Q",
            title="Questions Test",
            questions=[
                ClarifyingQuestion(
                    id="q1",
                    text="Required Q1",
                    category="scope",
                    required=True,
                    answer="Answer 1",
                ),
                ClarifyingQuestion(
                    id="q2",
                    text="Required Q2",
                    category="technical",
                    required=True,
                    answer="Answer 2",
                ),
            ],
        )
        assert contract.is_questions_complete() is True

    def test_is_questions_complete_missing_answer(
        self, contract_with_questions: TicketContract
    ):
        """is_questions_complete returns False when required question unanswered."""
        # Fixture has q1 with required=True and no answer
        assert contract_with_questions.is_questions_complete() is False

    def test_is_questions_complete_optional_unanswered_ok(self):
        """is_questions_complete ignores optional questions."""
        contract = TicketContract(
            ticket_id="OMN-OPT",
            title="Optional Test",
            questions=[
                ClarifyingQuestion(
                    id="q1",
                    text="Required",
                    category="scope",
                    required=True,
                    answer="Answered",
                ),
                ClarifyingQuestion(
                    id="q2",
                    text="Optional",
                    category="timeline",
                    required=False,
                    answer=None,  # Not answered but optional
                ),
            ],
        )
        assert contract.is_questions_complete() is True

    def test_is_questions_complete_whitespace_only_answer(self):
        """is_questions_complete treats whitespace-only answers as incomplete."""
        contract = TicketContract(
            ticket_id="OMN-WS",
            title="Whitespace Test",
            questions=[
                ClarifyingQuestion(
                    id="q1",
                    text="Required",
                    category="scope",
                    required=True,
                    answer="   ",  # Whitespace only
                ),
            ],
        )
        assert contract.is_questions_complete() is False

    # --- is_spec_complete ---

    def test_is_spec_complete_no_requirements(self, basic_contract: TicketContract):
        """is_spec_complete returns False when requirements list is empty."""
        assert basic_contract.requirements == []
        assert basic_contract.is_spec_complete() is False

    def test_is_spec_complete_missing_acceptance(self):
        """is_spec_complete returns False when requirement has no acceptance criteria."""
        contract = TicketContract(
            ticket_id="OMN-REQ",
            title="Req Test",
            requirements=[
                Requirement(
                    id="r1",
                    statement="Do something",
                    acceptance=[],  # Empty acceptance criteria
                ),
            ],
        )
        assert contract.is_spec_complete() is False

    def test_is_spec_complete_with_valid_requirements(self):
        """is_spec_complete returns True when all requirements have acceptance."""
        contract = TicketContract(
            ticket_id="OMN-VALID",
            title="Valid Spec",
            requirements=[
                Requirement(
                    id="r1",
                    statement="Requirement 1",
                    acceptance=["Criterion 1"],
                ),
                Requirement(
                    id="r2",
                    statement="Requirement 2",
                    acceptance=["Criterion A", "Criterion B"],
                ),
            ],
        )
        assert contract.is_spec_complete() is True

    # --- is_verification_complete ---

    def test_is_verification_complete_allows_skipped(self):
        """is_verification_complete treats skipped as complete."""
        contract = TicketContract(
            ticket_id="OMN-SKIP",
            title="Skip Test",
            verification_steps=[
                VerificationStep(
                    id="v1",
                    kind=VerificationKind.UNIT_TESTS,
                    blocking=True,
                    status=Status.SKIPPED,  # Skipped counts as complete
                ),
            ],
        )
        assert contract.is_verification_complete() is True

    def test_is_verification_complete_non_blocking_ignored(
        self, contract_with_verification: TicketContract
    ):
        """is_verification_complete ignores non-blocking steps."""
        # Fixture has v3 as non-blocking and pending
        # v1 is blocking+pending, v2 is blocking+passed
        # So should be False because v1 is blocking+pending
        assert contract_with_verification.is_verification_complete() is False

        # Update v1 to passed
        contract_with_verification.verification_steps = [
            VerificationStep(
                id="v1",
                kind=VerificationKind.UNIT_TESTS,
                blocking=True,
                status=Status.PASSED,
            ),
            contract_with_verification.verification_steps[1],  # v2 already passed
            contract_with_verification.verification_steps[2],  # v3 non-blocking
        ]
        assert contract_with_verification.is_verification_complete() is True

    def test_is_verification_complete_empty_list(self, basic_contract: TicketContract):
        """is_verification_complete returns True when no verification steps."""
        assert basic_contract.verification_steps == []
        assert basic_contract.is_verification_complete() is True

    # --- is_gates_complete ---

    def test_is_gates_complete_all_approved(self):
        """is_gates_complete returns True when all required gates approved."""
        contract = TicketContract(
            ticket_id="OMN-GATES-OK",
            title="Gates OK",
            gates=[
                Gate(
                    id="g1",
                    kind=GateKind.HUMAN_APPROVAL,
                    description="Gate 1",
                    required=True,
                    status=Status.APPROVED,
                ),
                Gate(
                    id="g2",
                    kind=GateKind.SECURITY_CHECK,
                    description="Gate 2",
                    required=True,
                    status=Status.APPROVED,
                ),
            ],
        )
        assert contract.is_gates_complete() is True

    def test_is_gates_complete_optional_ignored(self):
        """is_gates_complete ignores optional gates."""
        contract = TicketContract(
            ticket_id="OMN-OPT-GATE",
            title="Optional Gate",
            gates=[
                Gate(
                    id="g1",
                    kind=GateKind.HUMAN_APPROVAL,
                    description="Required",
                    required=True,
                    status=Status.APPROVED,
                ),
                Gate(
                    id="g2",
                    kind=GateKind.POLICY_CHECK,
                    description="Optional",
                    required=False,
                    status=Status.PENDING,  # Pending but optional
                ),
            ],
        )
        assert contract.is_gates_complete() is True

    # --- is_done ---

    def test_is_done_requires_phase_done(self, complete_contract: TicketContract):
        """is_done returns False if phase != DONE even if checks pass."""
        # Set phase to something other than DONE
        complete_contract.phase = Phase.REVIEW

        # All other checks would pass
        assert complete_contract.is_questions_complete() is True
        assert complete_contract.is_spec_complete() is True
        assert complete_contract.is_verification_complete() is True
        assert complete_contract.is_gates_complete() is True

        # But is_done should still be False
        assert complete_contract.is_done() is False

        # Set to DONE and now it should be True
        complete_contract.phase = Phase.DONE
        assert complete_contract.is_done() is True

    def test_is_done_complete_contract(self, complete_contract: TicketContract):
        """is_done returns True for fully complete contract."""
        assert complete_contract.is_done() is True

    def test_is_done_fails_incomplete_questions(
        self, complete_contract: TicketContract
    ):
        """is_done returns False if questions incomplete."""
        # Add an unanswered required question
        complete_contract.questions = [
            ClarifyingQuestion(
                id="q_new",
                text="New question",
                category="scope",
                required=True,
                answer=None,
            ),
        ]
        assert complete_contract.is_done() is False

    # --- pending_questions ---

    def test_pending_questions_returns_unanswered(
        self, contract_with_questions: TicketContract
    ):
        """pending_questions returns only required unanswered questions."""
        pending = contract_with_questions.pending_questions()

        # q1 is required and unanswered
        # q2 is required and answered
        # q3 is optional and unanswered
        assert len(pending) == 1
        assert pending[0].id == "q1"

    def test_pending_questions_empty_when_all_answered(self):
        """pending_questions returns empty list when all answered."""
        contract = TicketContract(
            ticket_id="OMN-ALL",
            title="All Answered",
            questions=[
                ClarifyingQuestion(
                    id="q1",
                    text="Question",
                    category="scope",
                    required=True,
                    answer="Answer",
                ),
            ],
        )
        assert contract.pending_questions() == []

    # --- blocking_verification ---

    def test_blocking_verification_filters_correctly(
        self, contract_with_verification: TicketContract
    ):
        """blocking_verification returns only blocking steps that haven't passed."""
        blocking = contract_with_verification.blocking_verification()

        # v1: blocking + pending (should be returned)
        # v2: blocking + passed (should NOT be returned)
        # v3: non-blocking + pending (should NOT be returned)
        assert len(blocking) == 1
        assert blocking[0].id == "v1"

    def test_blocking_verification_excludes_skipped(self):
        """blocking_verification excludes skipped steps."""
        contract = TicketContract(
            ticket_id="OMN-BLOCK",
            title="Blocking Test",
            verification_steps=[
                VerificationStep(
                    id="v1",
                    kind=VerificationKind.UNIT_TESTS,
                    blocking=True,
                    status=Status.SKIPPED,  # Should not be returned
                ),
            ],
        )
        assert contract.blocking_verification() == []

    # --- pending_gates ---

    def test_pending_gates_filters_correctly(self, contract_with_gates: TicketContract):
        """pending_gates returns only required gates that aren't approved."""
        pending = contract_with_gates.pending_gates()

        # g1: required + pending (should be returned)
        # g2: required + approved (should NOT be returned)
        # g3: optional + pending (should NOT be returned)
        assert len(pending) == 1
        assert pending[0].id == "g1"


# =============================================================================
# R6: Fingerprint Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprint:
    """Test fingerprint computation and update (R6)."""

    def test_fingerprint_is_16_char_hex(self, basic_contract: TicketContract):
        """compute_fingerprint returns a 16-character hex string."""
        fingerprint = basic_contract.compute_fingerprint()

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 16
        # Verify it's valid hex (only 0-9, a-f)
        assert re.match(r"^[0-9a-f]{16}$", fingerprint) is not None

    def test_fingerprint_excludes_fingerprint_field(
        self, basic_contract: TicketContract
    ):
        """compute_fingerprint excludes the contract_fingerprint field itself."""
        # Set a fingerprint
        basic_contract.contract_fingerprint = "original_fingerprint"

        # Compute new fingerprint
        fp1 = basic_contract.compute_fingerprint()

        # Change the fingerprint value
        basic_contract.contract_fingerprint = "different_fingerprint"

        # Fingerprint should be the same (it excludes its own field)
        fp2 = basic_contract.compute_fingerprint()

        assert fp1 == fp2

    def test_update_fingerprint_also_updates_updated_at(
        self, basic_contract: TicketContract
    ):
        """update_fingerprint updates both fingerprint and updated_at."""
        original_updated_at = basic_contract.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        basic_contract.update_fingerprint()

        assert basic_contract.contract_fingerprint is not None
        assert len(basic_contract.contract_fingerprint) == 16
        assert basic_contract.updated_at > original_updated_at

    def test_fingerprint_changes_with_content(self, basic_contract: TicketContract):
        """Fingerprint changes when contract content changes."""
        fp1 = basic_contract.compute_fingerprint()

        basic_contract.title = "Different Title"
        fp2 = basic_contract.compute_fingerprint()

        assert fp1 != fp2

    def test_fingerprint_deterministic(self, basic_contract: TicketContract):
        """Fingerprint is deterministic for same content."""
        fp1 = basic_contract.compute_fingerprint()
        fp2 = basic_contract.compute_fingerprint()

        assert fp1 == fp2


# =============================================================================
# R8: YAML Round-Trip Tests
# =============================================================================


@pytest.mark.unit
class TestYAMLSerialization:
    """Test YAML serialization and deserialization (R8)."""

    def test_to_yaml_produces_readable_output(self, basic_contract: TicketContract):
        """to_yaml produces human-readable YAML output."""
        yaml_output = basic_contract.to_yaml()

        # Should be valid YAML
        parsed = yaml.safe_load(yaml_output)
        assert isinstance(parsed, dict)

        # Should contain expected fields
        assert "ticket_id" in yaml_output
        assert "OMN-TEST" in yaml_output
        assert "title" in yaml_output
        assert "Test Ticket" in yaml_output

    def test_yaml_round_trip_preserves_data(self, complete_contract: TicketContract):
        """Round-trip through YAML preserves all data."""
        # Serialize
        yaml_output = complete_contract.to_yaml()

        # Deserialize
        restored = TicketContract.from_yaml(yaml_output)

        # Core fields preserved
        assert restored.ticket_id == complete_contract.ticket_id
        assert restored.title == complete_contract.title
        assert restored.phase == complete_contract.phase

        # Complex fields preserved
        assert len(restored.questions) == len(complete_contract.questions)
        assert len(restored.requirements) == len(complete_contract.requirements)
        assert len(restored.verification_steps) == len(
            complete_contract.verification_steps
        )
        assert len(restored.gates) == len(complete_contract.gates)

        # Nested data preserved
        assert restored.requirements[0].acceptance == ["Given/When/Then criteria"]

    def test_yaml_enums_serialize_as_strings(self, basic_contract: TicketContract):
        """Enums in YAML are plain strings, not !!python/object."""
        basic_contract.phase = Phase.IMPLEMENTATION

        yaml_output = basic_contract.to_yaml()

        # Should not contain Python-specific tags
        assert "!!python" not in yaml_output
        assert "EnumTicketPhase" not in yaml_output

        # Should contain plain string value
        assert "phase: implementation" in yaml_output

    def test_from_yaml_invalid_yaml_raises(self):
        """from_yaml raises ModelOnexError for invalid YAML."""
        invalid_yaml = "this: is: not: valid: yaml: {{"

        with pytest.raises(ModelOnexError) as exc_info:
            TicketContract.from_yaml(invalid_yaml)

        assert "parse" in str(exc_info.value).lower()

    def test_from_yaml_non_dict_raises(self):
        """from_yaml raises ModelOnexError when YAML is not a dict."""
        list_yaml = "- item1\n- item2\n"

        with pytest.raises(ModelOnexError) as exc_info:
            TicketContract.from_yaml(list_yaml)

        assert "dict" in str(exc_info.value).lower()

    def test_yaml_datetime_serialization(self, complete_contract: TicketContract):
        """Datetime fields serialize and deserialize correctly in YAML."""
        yaml_output = complete_contract.to_yaml()
        restored = TicketContract.from_yaml(yaml_output)

        # Datetimes should be preserved (though may have microsecond differences)
        assert isinstance(restored.created_at, datetime)
        assert isinstance(restored.updated_at, datetime)


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Additional edge case tests for robustness."""

    def test_contract_with_empty_description(self):
        """Contract can be created with empty description (default)."""
        contract = TicketContract(
            ticket_id="OMN-EMPTY",
            title="Empty Desc",
        )
        assert contract.description == ""

    def test_contract_with_context_dict(self):
        """Contract context dict works correctly."""
        contract = TicketContract(
            ticket_id="OMN-CTX",
            title="Context Test",
            context={
                "key1": "value1",
                "nested": {"inner": "data"},
                "list": [1, 2, 3],
            },
        )
        assert contract.context["key1"] == "value1"
        assert contract.context["nested"]["inner"] == "data"
        assert contract.context["list"] == [1, 2, 3]

    def test_frozen_sub_models(self):
        """Sub-models (ClarifyingQuestion, etc.) are frozen/immutable."""
        question = ClarifyingQuestion(
            id="q1",
            text="Question",
            category="scope",
        )

        # Should raise ValidationError when trying to modify frozen model
        with pytest.raises(ValidationError):
            question.text = "Modified"  # type: ignore[misc]

    def test_main_contract_is_mutable(self, basic_contract: TicketContract):
        """Main TicketContract is mutable (not frozen)."""
        original_title = basic_contract.title
        basic_contract.title = "Modified Title"

        assert basic_contract.title == "Modified Title"
        assert basic_contract.title != original_title

    def test_model_dump_mode_json(self, complete_contract: TicketContract):
        """model_dump(mode='json') produces JSON-serializable output."""
        dumped = complete_contract.model_dump(mode="json")

        # Should be JSON serializable
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)

        # Enums should be strings
        assert isinstance(dumped["phase"], str)
        assert dumped["phase"] == "done"

    def test_question_categories_literal(self):
        """ClarifyingQuestion category is constrained to valid literals."""
        valid_categories = [
            "scope",
            "technical",
            "acceptance",
            "timeline",
            "dependency",
        ]

        for cat in valid_categories:
            q = ClarifyingQuestion(id="q", text="Q", category=cat)  # type: ignore[arg-type]
            assert q.category == cat

    def test_extra_fields_allowed_on_contract(self):
        """TicketContract allows extra fields for extensibility."""
        # Create via model_validate to include extra field
        data = {
            "ticket_id": "OMN-EXTRA",
            "title": "Extra Fields Test",
            "custom_field": "custom_value",  # Extra field
        }
        contract = TicketContract.model_validate(data)

        # Extra field should be accessible
        assert getattr(contract, "custom_field", None) == "custom_value"
