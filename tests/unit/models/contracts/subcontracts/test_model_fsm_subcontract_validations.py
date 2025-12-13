"""
Tests for ModelFSMSubcontract validation rules.

This module tests the new validation rules added in OMN-575:
1. validate_unique_transition_names - No duplicate transition names
2. validate_unique_structural_transitions - No duplicate (from_state, trigger, priority) tuples
3. validate_no_transitions_from_terminal_states - Terminal states cannot have outgoing transitions
"""

import pytest

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances
DEFAULT_VERSION = ModelSemVer(major=1, minor=5, patch=0)


def create_minimal_fsm_subcontract(
    states: list[ModelFSMStateDefinition],
    transitions: list[ModelFSMStateTransition],
    initial_state: str = "pending",
    terminal_states: list[str] | None = None,
) -> ModelFSMSubcontract:
    """Create a minimal valid FSM subcontract for testing."""
    return ModelFSMSubcontract(
        version=DEFAULT_VERSION,
        state_machine_name="test_fsm",
        state_machine_version=DEFAULT_VERSION,
        description="Test FSM",
        states=states,
        initial_state=initial_state,
        terminal_states=terminal_states or [],
        transitions=transitions,
    )


def create_state(
    state_name: str,
    is_terminal: bool = False,
    is_recoverable: bool | None = None,
) -> ModelFSMStateDefinition:
    """Helper to create a state definition."""
    # Terminal states cannot be recoverable
    if is_recoverable is None:
        is_recoverable = not is_terminal
    return ModelFSMStateDefinition(
        version=DEFAULT_VERSION,
        state_name=state_name,
        state_type="operational",
        description=f"State {state_name}",
        is_terminal=is_terminal,
        is_recoverable=is_recoverable,
    )


def create_transition(
    transition_name: str,
    from_state: str,
    to_state: str,
    trigger: str,
    priority: int = 0,
) -> ModelFSMStateTransition:
    """Helper to create a transition."""
    return ModelFSMStateTransition(
        version=DEFAULT_VERSION,
        transition_name=transition_name,
        from_state=from_state,
        to_state=to_state,
        trigger=trigger,
        priority=priority,
    )


class TestUniqueTransitionNames:
    """Tests for validate_unique_transition_names validation."""

    def test_duplicate_transition_names_rejected(self) -> None:
        """Verify duplicate transition names fail validation."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("completed"),
        ]
        transitions = [
            create_transition("start", "pending", "processing", "begin"),
            create_transition(
                "start", "processing", "completed", "finish"
            ),  # Duplicate name
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(states=states, transitions=transitions)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Duplicate transition names found" in str(exc_info.value)
        assert "start" in str(exc_info.value)

    def test_unique_transition_names_allowed(self) -> None:
        """Positive case: unique transition names should succeed."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("completed"),
        ]
        transitions = [
            create_transition("start_processing", "pending", "processing", "begin"),
            create_transition("finish_processing", "processing", "completed", "finish"),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states, transitions=transitions
        )

        assert subcontract is not None
        assert len(subcontract.transitions) == 2

    def test_multiple_duplicates_all_reported(self) -> None:
        """Verify all duplicates are reported in the error message."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("review"),
            create_state("completed"),
        ]
        transitions = [
            create_transition("action_a", "pending", "processing", "begin"),
            create_transition("action_b", "processing", "review", "review"),
            create_transition(
                "action_a", "review", "completed", "complete"
            ),  # Duplicate
            create_transition("action_b", "pending", "review", "skip"),  # Duplicate
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(states=states, transitions=transitions)

        error_message = str(exc_info.value)
        assert "Duplicate transition names found" in error_message
        assert "action_a" in error_message
        assert "action_b" in error_message


class TestUniqueStructuralTransitions:
    """Tests for validate_unique_structural_transitions validation."""

    def test_duplicate_structural_transitions_rejected(self) -> None:
        """Same (from_state, trigger, priority) tuple should fail validation."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("review"),
        ]
        transitions = [
            create_transition(
                "transition_1", "pending", "processing", "submit", priority=0
            ),
            create_transition(
                "transition_2", "pending", "review", "submit", priority=0
            ),  # Same struct
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(states=states, transitions=transitions)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Duplicate structural transitions found" in str(exc_info.value)
        assert "from_state='pending'" in str(exc_info.value)
        assert "trigger='submit'" in str(exc_info.value)
        assert "priority=0" in str(exc_info.value)

    def test_same_from_state_trigger_different_priority_allowed(self) -> None:
        """Different priorities OK: two transitions with same from_state and trigger but different priority."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("review"),
        ]
        transitions = [
            create_transition(
                "high_priority_submit", "pending", "processing", "submit", priority=10
            ),
            create_transition(
                "low_priority_submit", "pending", "review", "submit", priority=5
            ),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states, transitions=transitions
        )

        assert subcontract is not None
        assert len(subcontract.transitions) == 2

    def test_same_trigger_different_from_state_allowed(self) -> None:
        """Same trigger from different states is allowed."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("completed"),
        ]
        transitions = [
            create_transition(
                "transition_1", "pending", "processing", "advance", priority=0
            ),
            create_transition(
                "transition_2", "processing", "completed", "advance", priority=0
            ),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states, transitions=transitions
        )

        assert subcontract is not None
        assert len(subcontract.transitions) == 2

    def test_same_from_state_different_trigger_allowed(self) -> None:
        """Same from_state with different triggers is allowed."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("cancelled"),
        ]
        transitions = [
            create_transition("start", "pending", "processing", "submit", priority=0),
            create_transition("cancel", "pending", "cancelled", "cancel", priority=0),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states, transitions=transitions
        )

        assert subcontract is not None
        assert len(subcontract.transitions) == 2


class TestNoTransitionsFromTerminalStates:
    """Tests for validate_no_transitions_from_terminal_states validation."""

    def test_transitions_from_terminal_state_rejected(self) -> None:
        """Terminal state with outgoing transition should fail validation."""
        states = [
            create_state("pending"),
            create_state("completed", is_terminal=True),
            create_state("archived"),
        ]
        transitions = [
            create_transition("complete", "pending", "completed", "finish"),
            create_transition(
                "archive", "completed", "archived", "archive"
            ),  # Invalid: from terminal
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(
                states=states,
                transitions=transitions,
                terminal_states=["completed"],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Transitions from terminal states are not allowed" in str(exc_info.value)
        assert "completed" in str(exc_info.value)
        assert "archive" in str(exc_info.value)

    def test_terminal_state_via_terminal_states_list(self) -> None:
        """Terminal states declared via terminal_states list should also be checked."""
        states = [
            create_state("pending"),
            create_state("done"),  # Not marked as terminal in definition
            create_state("archived"),
        ]
        transitions = [
            create_transition("complete", "pending", "done", "finish"),
            create_transition("archive", "done", "archived", "archive"),  # Invalid
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(
                states=states,
                transitions=transitions,
                terminal_states=["done"],  # Declared terminal via list
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Transitions from terminal states are not allowed" in str(exc_info.value)

    def test_wildcard_transitions_always_allowed(self) -> None:
        """Wildcard from '*' is OK: even if target matches terminal state, wildcard is from '*' not from terminal."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("completed", is_terminal=True),
            create_state("error"),
        ]
        transitions = [
            create_transition("start", "pending", "processing", "begin"),
            create_transition("complete", "processing", "completed", "finish"),
            # Wildcard transition - should be allowed even though completed is terminal
            create_transition("global_error", "*", "error", "error_occurred"),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states,
            transitions=transitions,
            terminal_states=["completed"],
        )

        assert subcontract is not None
        # Verify wildcard transition exists
        wildcard_transitions = [
            t for t in subcontract.transitions if t.from_state == "*"
        ]
        assert len(wildcard_transitions) == 1
        assert wildcard_transitions[0].transition_name == "global_error"

    def test_non_terminal_states_can_have_outgoing_transitions(self) -> None:
        """Non-terminal states should be able to have outgoing transitions."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("review"),
            create_state("completed", is_terminal=True),
        ]
        transitions = [
            create_transition("start", "pending", "processing", "begin"),
            create_transition("submit_review", "processing", "review", "review"),
            create_transition("complete", "review", "completed", "approve"),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states,
            transitions=transitions,
            terminal_states=["completed"],
        )

        assert subcontract is not None
        assert len(subcontract.transitions) == 3

    def test_multiple_terminal_states_all_checked(self) -> None:
        """All terminal states should be checked for outgoing transitions."""
        states = [
            create_state("pending"),
            create_state("completed", is_terminal=True),
            create_state("cancelled", is_terminal=True),
            create_state("archived"),
        ]
        transitions = [
            create_transition("complete", "pending", "completed", "finish"),
            create_transition("cancel", "pending", "cancelled", "cancel"),
            create_transition(
                "archive_completed", "completed", "archived", "archive"
            ),  # Invalid
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(
                states=states,
                transitions=transitions,
                terminal_states=["completed", "cancelled"],
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "completed" in str(exc_info.value)


class TestValidationInteractions:
    """Test interactions between multiple validations."""

    def test_all_validations_pass_for_valid_contract(self) -> None:
        """A well-formed contract should pass all validations."""
        states = [
            create_state("pending"),
            create_state("processing"),
            create_state("review"),
            create_state("completed", is_terminal=True),
            create_state("cancelled", is_terminal=True),
            create_state("error"),
        ]
        transitions = [
            create_transition(
                "start_processing", "pending", "processing", "submit", priority=10
            ),
            create_transition(
                "request_review", "processing", "review", "review", priority=0
            ),
            create_transition("approve", "review", "completed", "approve", priority=0),
            create_transition("reject", "review", "processing", "reject", priority=0),
            create_transition(
                "cancel_pending", "pending", "cancelled", "cancel", priority=0
            ),
            create_transition(
                "cancel_processing", "processing", "cancelled", "cancel", priority=0
            ),
            # Wildcard for global error handling
            create_transition(
                "global_error_handler", "*", "error", "system_error", priority=100
            ),
        ]

        subcontract = create_minimal_fsm_subcontract(
            states=states,
            transitions=transitions,
            terminal_states=["completed", "cancelled"],
        )

        assert subcontract is not None
        assert subcontract.state_machine_name == "test_fsm"
        assert len(subcontract.states) == 6
        assert len(subcontract.transitions) == 7

    def test_duplicate_names_caught_before_structural_check(self) -> None:
        """Duplicate names validation should catch issues even if structural would also fail."""
        states = [
            create_state("pending"),
            create_state("processing"),
        ]
        # Both have duplicate name AND duplicate structure
        transitions = [
            create_transition("action", "pending", "processing", "go", priority=0),
            create_transition("action", "pending", "processing", "go", priority=0),
        ]

        with pytest.raises(ModelOnexError) as exc_info:
            create_minimal_fsm_subcontract(states=states, transitions=transitions)

        # Both errors could be caught, but duplicate names is explicit
        error_message = str(exc_info.value)
        assert "Duplicate" in error_message
