"""
Unit tests for FSM (Finite State Machine) Analysis Module.

TDD Tests for OMN-175: Write tests FIRST before implementation.

Tests comprehensive FSM validation functionality including:
- Unreachable states detection
- Cycles without exit paths
- Ambiguous transitions
- Dead transitions (unreachable)
- Missing transitions (dead-ends)
- Duplicate state names
- Valid FSM scenarios

All tests are expected to FAIL initially until implementation is complete.
"""

import pytest

from omnibase_core.models.contracts.subcontracts.model_fsm_operation import (
    ModelFSMOperation,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import the module under test
from omnibase_core.validation.fsm_analysis import (
    ModelAmbiguousTransition,
    ModelFSMAnalysisResult,
    analyze_fsm,
)

# ==================== Test Fixtures ====================


@pytest.fixture
def base_version() -> ModelSemVer:
    """Common version for all test fixtures."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def valid_fsm(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    Valid FSM: idle → processing → completed.

    Simple linear flow with no issues:
    - Initial state: idle
    - Terminal state: completed
    - All states reachable from initial
    - No cycles without exit
    - No ambiguous transitions
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial idle state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="processing",
            state_type="operational",
            description="Processing work",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Work completed successfully",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="start_processing",
            from_state="idle",
            to_state="processing",
            trigger="start",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="complete_processing",
            from_state="processing",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="ValidWorkflow",
        state_machine_version=base_version,
        description="Simple valid FSM for testing",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_unreachable_state(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM with orphan state that cannot be reached from initial state.

    Structure:
    - idle → processing → completed (valid path)
    - orphan (no incoming transitions from initial)

    Expected issue: unreachable_states = ["orphan"]
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="processing",
            state_type="operational",
            description="Processing state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="orphan",
            state_type="operational",
            description="Unreachable orphan state",
            is_terminal=False,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="start",
            from_state="idle",
            to_state="processing",
            trigger="start",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="finish",
            from_state="processing",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
        # orphan → completed exists, but orphan is unreachable from initial
        ModelFSMStateTransition(
            version=base_version,
            transition_name="orphan_finish",
            from_state="orphan",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithOrphan",
        state_machine_version=base_version,
        description="FSM with unreachable orphan state",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_cycle_no_exit(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM with infinite cycle A → B → C → A with no path to terminal.

    Structure:
    - idle (initial)
    - stateA → stateB → stateC → stateA (infinite loop)
    - completed (terminal, but unreachable from cycle)

    Expected issue: cycles_without_exit = [["stateA", "stateB", "stateC"]]
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateA",
            state_type="operational",
            description="Part of cycle",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateB",
            state_type="operational",
            description="Part of cycle",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateC",
            state_type="operational",
            description="Part of cycle",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="enter_cycle",
            from_state="idle",
            to_state="stateA",
            trigger="start",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="a_to_b",
            from_state="stateA",
            to_state="stateB",
            trigger="next",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="b_to_c",
            from_state="stateB",
            to_state="stateC",
            trigger="next",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="c_to_a",
            from_state="stateC",
            to_state="stateA",
            trigger="next",
            priority=1,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithCycleNoExit",
        state_machine_version=base_version,
        description="FSM with infinite cycle and no exit path",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_cycle_and_exit(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM with cycle A → B → A but B also has exit to terminal.

    Structure:
    - idle → stateA → stateB → stateA (cycle)
    - stateB → completed (exit from cycle)

    Expected: VALID (no cycles_without_exit because exit path exists)
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateA",
            state_type="operational",
            description="Part of cycle with exit",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateB",
            state_type="operational",
            description="Part of cycle with exit",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="enter_cycle",
            from_state="idle",
            to_state="stateA",
            trigger="start",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="a_to_b",
            from_state="stateA",
            to_state="stateB",
            trigger="continue",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="b_to_a",
            from_state="stateB",
            to_state="stateA",
            trigger="retry",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="b_to_completed",
            from_state="stateB",
            to_state="completed",
            trigger="finish",
            priority=2,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithCycleAndExit",
        state_machine_version=base_version,
        description="FSM with cycle but also valid exit path",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_ambiguous_transitions(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM where (state_A, event_X) maps to BOTH state_B AND state_C.

    Structure:
    - idle → processing
    - processing + trigger "ambiguous" → stateB (priority 1)
    - processing + trigger "ambiguous" → stateC (priority 1)

    Expected issue: ambiguous_transitions for (processing, ambiguous)
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="processing",
            state_type="operational",
            description="State with ambiguous transitions",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateB",
            state_type="operational",
            description="First ambiguous target",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateC",
            state_type="operational",
            description="Second ambiguous target",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="start",
            from_state="idle",
            to_state="processing",
            trigger="start",
            priority=1,
        ),
        # AMBIGUOUS: same from_state + trigger with SAME priority
        ModelFSMStateTransition(
            version=base_version,
            transition_name="ambiguous_to_b",
            from_state="processing",
            to_state="stateB",
            trigger="ambiguous",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="ambiguous_to_c",
            from_state="processing",
            to_state="stateC",
            trigger="ambiguous",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="b_to_completed",
            from_state="stateB",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="c_to_completed",
            from_state="stateC",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithAmbiguousTransitions",
        state_machine_version=base_version,
        description="FSM with ambiguous transitions",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_wildcard_transitions(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM with wildcard '*' and specific state with same trigger.

    Structure:
    - '*' + trigger "error" → error_state (global error handler)
    - processing + trigger "error" → retry_state (specific override)

    Expected: NOT ambiguous (specific takes precedence over wildcard)
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="processing",
            state_type="operational",
            description="Processing state with specific error handler",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="retry_state",
            state_type="operational",
            description="Specific error recovery",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="error_state",
            state_type="error",
            description="Global error state",
            is_terminal=True,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="start",
            from_state="idle",
            to_state="processing",
            trigger="start",
            priority=1,
        ),
        # Wildcard transition (global error handler)
        ModelFSMStateTransition(
            version=base_version,
            transition_name="global_error",
            from_state="*",
            to_state="error_state",
            trigger="error",
            priority=1,
        ),
        # Specific transition (overrides wildcard for processing state)
        ModelFSMStateTransition(
            version=base_version,
            transition_name="processing_error",
            from_state="processing",
            to_state="retry_state",
            trigger="error",
            priority=2,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="retry_to_completed",
            from_state="retry_state",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithWildcard",
        state_machine_version=base_version,
        description="FSM with wildcard and specific transitions",
        states=states,
        initial_state="idle",
        terminal_states=["completed", "error_state"],
        error_states=["error_state"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_dead_end_state(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM with non-terminal state that has no outgoing transitions (dead-end).

    Structure:
    - idle → processing → dead_end (no transitions out)
    - completed is terminal but unreachable

    Expected issue: missing_transitions for dead_end state
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="processing",
            state_type="operational",
            description="Processing state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="dead_end",
            state_type="operational",
            description="Dead-end state with no exits",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="start",
            from_state="idle",
            to_state="processing",
            trigger="start",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="to_dead_end",
            from_state="processing",
            to_state="dead_end",
            trigger="fail",
            priority=1,
        ),
        # No transitions from dead_end!
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithDeadEnd",
        state_machine_version=base_version,
        description="FSM with dead-end non-terminal state",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


@pytest.fixture
def fsm_with_multiple_issues(base_version: ModelSemVer) -> ModelFSMSubcontract:
    """
    FSM with multiple validation issues to test comprehensive reporting.

    Issues:
    1. Unreachable state: orphan
    2. Ambiguous transitions: processing + "ambiguous"
    3. Dead-end state: dead_end (non-terminal with no exits)
    4. Cycle without exit: cycleA → cycleB → cycleA

    All issues should be reported, not just the first one found.
    """
    states = [
        ModelFSMStateDefinition(
            version=base_version,
            state_name="idle",
            state_type="operational",
            description="Initial state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="processing",
            state_type="operational",
            description="State with ambiguous transitions",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateB",
            state_type="operational",
            description="Ambiguous target 1",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="stateC",
            state_type="operational",
            description="Ambiguous target 2",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="dead_end",
            state_type="operational",
            description="Dead-end state",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="orphan",
            state_type="operational",
            description="Unreachable orphan",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="cycleA",
            state_type="operational",
            description="Part of infinite cycle",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="cycleB",
            state_type="operational",
            description="Part of infinite cycle",
            is_terminal=False,
        ),
        ModelFSMStateDefinition(
            version=base_version,
            state_name="completed",
            state_type="terminal",
            description="Terminal state",
            is_terminal=True,
        ),
    ]

    transitions = [
        ModelFSMStateTransition(
            version=base_version,
            transition_name="start",
            from_state="idle",
            to_state="processing",
            trigger="start",
            priority=1,
        ),
        # Ambiguous transitions
        ModelFSMStateTransition(
            version=base_version,
            transition_name="ambiguous_b",
            from_state="processing",
            to_state="stateB",
            trigger="ambiguous",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="ambiguous_c",
            from_state="processing",
            to_state="stateC",
            trigger="ambiguous",
            priority=1,
        ),
        # Dead-end transition
        ModelFSMStateTransition(
            version=base_version,
            transition_name="to_dead_end",
            from_state="stateB",
            to_state="dead_end",
            trigger="fail",
            priority=1,
        ),
        # Infinite cycle
        ModelFSMStateTransition(
            version=base_version,
            transition_name="to_cycle",
            from_state="stateC",
            to_state="cycleA",
            trigger="loop",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="cycle_a_to_b",
            from_state="cycleA",
            to_state="cycleB",
            trigger="next",
            priority=1,
        ),
        ModelFSMStateTransition(
            version=base_version,
            transition_name="cycle_b_to_a",
            from_state="cycleB",
            to_state="cycleA",
            trigger="next",
            priority=1,
        ),
        # Orphan has transition but is unreachable
        ModelFSMStateTransition(
            version=base_version,
            transition_name="orphan_exit",
            from_state="orphan",
            to_state="completed",
            trigger="finish",
            priority=1,
        ),
    ]

    return ModelFSMSubcontract(
        version=base_version,
        state_machine_name="FSMWithMultipleIssues",
        state_machine_version=base_version,
        description="FSM with multiple validation issues",
        states=states,
        initial_state="idle",
        terminal_states=["completed"],
        transitions=transitions,
    )


# ==================== Test Cases ====================


class TestFSMAnalysisUnreachableStates:
    """Test detection of unreachable states."""

    def test_detect_unreachable_states(
        self, fsm_with_unreachable_state: ModelFSMSubcontract
    ) -> None:
        """
        Test that unreachable states are detected.

        The orphan state has no path from initial state, so it should be
        flagged as unreachable.
        """
        result = analyze_fsm(fsm_with_unreachable_state)

        assert not result.is_valid, "FSM with unreachable state should be invalid"
        assert len(result.unreachable_states) == 1
        assert "orphan" in result.unreachable_states
        assert any("unreachable" in error.lower() for error in result.errors)

    def test_valid_fsm_has_no_unreachable_states(
        self, valid_fsm: ModelFSMSubcontract
    ) -> None:
        """
        Test that valid FSM has no unreachable states.

        All states in valid FSM should be reachable from initial state.
        """
        result = analyze_fsm(valid_fsm)

        assert result.is_valid
        assert len(result.unreachable_states) == 0


class TestFSMAnalysisCycles:
    """Test detection of cycles with and without exit paths."""

    def test_detect_cycle_without_exit(
        self, fsm_with_cycle_no_exit: ModelFSMSubcontract
    ) -> None:
        """
        Test that cycles without exit paths are detected.

        The cycle stateA → stateB → stateC → stateA has no path to terminal,
        so it should be flagged.
        """
        result = analyze_fsm(fsm_with_cycle_no_exit)

        assert not result.is_valid, "FSM with cycle and no exit should be invalid"
        assert len(result.cycles_without_exit) > 0
        # Verify the cycle contains all three states
        cycle_states = set(result.cycles_without_exit[0])
        assert {"stateA", "stateB", "stateC"}.issubset(cycle_states)
        assert any("cycle" in error.lower() for error in result.errors)

    def test_cycle_with_exit_is_valid(
        self, fsm_with_cycle_and_exit: ModelFSMSubcontract
    ) -> None:
        """
        Test that cycles WITH exit paths are considered valid.

        The cycle stateA → stateB → stateA has an exit (stateB → completed),
        so it should NOT be flagged as problematic.
        """
        result = analyze_fsm(fsm_with_cycle_and_exit)

        # This should be valid because there's an exit from the cycle
        assert result.is_valid, "FSM with cycle and exit should be valid"
        assert len(result.cycles_without_exit) == 0

    def test_valid_fsm_has_no_problematic_cycles(
        self, valid_fsm: ModelFSMSubcontract
    ) -> None:
        """
        Test that valid FSM has no cycles without exit.

        Simple linear flow should have no cycles at all.
        """
        result = analyze_fsm(valid_fsm)

        assert result.is_valid
        assert len(result.cycles_without_exit) == 0


class TestFSMAnalysisAmbiguousTransitions:
    """Test detection of ambiguous transitions."""

    def test_detect_ambiguous_transitions(
        self, fsm_with_ambiguous_transitions: ModelFSMSubcontract
    ) -> None:
        """
        Test that ambiguous transitions are detected.

        When (state, trigger) maps to multiple targets with same priority,
        it should be flagged as ambiguous.
        """
        result = analyze_fsm(fsm_with_ambiguous_transitions)

        assert not result.is_valid, "FSM with ambiguous transitions should be invalid"
        assert len(result.ambiguous_transitions) > 0

        # Check that the ambiguous transition is reported
        found = any(
            amb.from_state == "processing" and amb.trigger == "ambiguous"
            for amb in result.ambiguous_transitions
        )
        assert found, "Expected ambiguous transition for (processing, ambiguous)"
        assert any("ambiguous" in error.lower() for error in result.errors)

    def test_wildcard_transitions_not_ambiguous(
        self, fsm_with_wildcard_transitions: ModelFSMSubcontract
    ) -> None:
        """
        Test that wildcard '*' and specific state with same trigger is NOT ambiguous.

        Specific state transitions should take precedence over wildcard,
        so this is not considered ambiguous.
        """
        result = analyze_fsm(fsm_with_wildcard_transitions)

        # Should be valid - specific takes precedence over wildcard
        assert result.is_valid, "Wildcard with specific override should be valid"
        assert len(result.ambiguous_transitions) == 0

    def test_different_priority_not_ambiguous(self, base_version: ModelSemVer) -> None:
        """
        Test that same (state, trigger) with DIFFERENT priorities is NOT ambiguous.

        Different priorities provide deterministic resolution, so not ambiguous.
        """
        states = [
            ModelFSMStateDefinition(
                version=base_version,
                state_name="idle",
                state_type="operational",
                description="Initial",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="processing",
                state_type="operational",
                description="Processing",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="stateB",
                state_type="operational",
                description="Target B",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="stateC",
                state_type="operational",
                description="Target C",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="completed",
                state_type="terminal",
                description="Terminal",
                is_terminal=True,
            ),
        ]

        transitions = [
            ModelFSMStateTransition(
                version=base_version,
                transition_name="start",
                from_state="idle",
                to_state="processing",
                trigger="start",
                priority=1,
            ),
            # Same from_state + trigger but DIFFERENT priority (not ambiguous)
            ModelFSMStateTransition(
                version=base_version,
                transition_name="high_priority",
                from_state="processing",
                to_state="stateB",
                trigger="event",
                priority=2,  # Higher priority
            ),
            ModelFSMStateTransition(
                version=base_version,
                transition_name="low_priority",
                from_state="processing",
                to_state="stateC",
                trigger="event",
                priority=1,  # Lower priority
            ),
            ModelFSMStateTransition(
                version=base_version,
                transition_name="finish_b",
                from_state="stateB",
                to_state="completed",
                trigger="finish",
                priority=1,
            ),
            ModelFSMStateTransition(
                version=base_version,
                transition_name="finish_c",
                from_state="stateC",
                to_state="completed",
                trigger="finish",
                priority=1,
            ),
        ]

        fsm = ModelFSMSubcontract(
            version=base_version,
            state_machine_name="DifferentPriority",
            state_machine_version=base_version,
            description="FSM with different priorities",
            states=states,
            initial_state="idle",
            terminal_states=["completed"],
            transitions=transitions,
        )

        result = analyze_fsm(fsm)

        # Should be valid - different priorities resolve deterministically
        assert result.is_valid, "Different priorities should not be ambiguous"
        assert len(result.ambiguous_transitions) == 0


class TestFSMAnalysisMissingTransitions:
    """Test detection of missing transitions (dead-end states)."""

    def test_detect_dead_end_state(
        self, fsm_with_dead_end_state: ModelFSMSubcontract
    ) -> None:
        """
        Test that non-terminal states without outgoing transitions are detected.

        A non-terminal state with no outgoing transitions is a dead-end.
        """
        result = analyze_fsm(fsm_with_dead_end_state)

        assert not result.is_valid, "FSM with dead-end state should be invalid"
        assert len(result.missing_transitions) > 0
        assert "dead_end" in result.missing_transitions
        assert any("missing" in error.lower() for error in result.errors)

    def test_terminal_state_without_transitions_is_valid(
        self, valid_fsm: ModelFSMSubcontract
    ) -> None:
        """
        Test that terminal states without outgoing transitions are valid.

        Terminal states are expected to have no outgoing transitions.
        """
        result = analyze_fsm(valid_fsm)

        assert result.is_valid
        # Terminal state "completed" should NOT be in missing_transitions
        assert "completed" not in result.missing_transitions


class TestFSMAnalysisValidFSM:
    """Test that valid FSMs pass all checks."""

    def test_valid_fsm_returns_no_issues(self, valid_fsm: ModelFSMSubcontract) -> None:
        """
        Test that a well-formed FSM passes all validation checks.

        A valid FSM should have:
        - is_valid = True
        - Empty error lists (unreachable, cycles, ambiguous, etc.)
        - Empty errors list
        """
        result = analyze_fsm(valid_fsm)

        assert result.is_valid, "Valid FSM should pass validation"
        assert len(result.unreachable_states) == 0
        assert len(result.cycles_without_exit) == 0
        assert len(result.ambiguous_transitions) == 0
        assert len(result.dead_transitions) == 0
        assert len(result.missing_transitions) == 0
        assert len(result.errors) == 0


class TestFSMAnalysisComprehensiveReporting:
    """Test that all issues are reported, not just the first."""

    def test_all_issues_reported_not_just_first(
        self, fsm_with_multiple_issues: ModelFSMSubcontract
    ) -> None:
        """
        Test that analysis reports ALL issues, not stopping at first problem.

        FSM has multiple issues:
        - Unreachable state (orphan)
        - Ambiguous transitions (processing + ambiguous)
        - Dead-end state (dead_end)
        - Cycle without exit (cycleA ↔ cycleB)

        All should be reported in the result.
        """
        result = analyze_fsm(fsm_with_multiple_issues)

        assert not result.is_valid, "FSM with multiple issues should be invalid"

        # Check unreachable states
        assert len(result.unreachable_states) > 0, "Should detect unreachable states"
        assert "orphan" in result.unreachable_states

        # Check ambiguous transitions
        assert len(result.ambiguous_transitions) > 0, (
            "Should detect ambiguous transitions"
        )

        # Check dead-end states
        assert len(result.missing_transitions) > 0, "Should detect missing transitions"
        assert "dead_end" in result.missing_transitions

        # Check cycles without exit
        assert len(result.cycles_without_exit) > 0, "Should detect cycles without exit"

        # Multiple errors should be reported
        assert len(result.errors) >= 3, "Should report multiple errors"

    def test_analysis_result_structure(self, valid_fsm: ModelFSMSubcontract) -> None:
        """
        Test that ModelFSMAnalysisResult has expected structure.

        Verify all required fields are present.
        """
        result = analyze_fsm(valid_fsm)

        # Check required fields exist
        assert hasattr(result, "is_valid")
        assert hasattr(result, "unreachable_states")
        assert hasattr(result, "cycles_without_exit")
        assert hasattr(result, "ambiguous_transitions")
        assert hasattr(result, "dead_transitions")
        assert hasattr(result, "missing_transitions")
        assert hasattr(result, "errors")

        # Check types
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.unreachable_states, list)
        assert isinstance(result.cycles_without_exit, list)
        assert isinstance(result.ambiguous_transitions, list)
        assert isinstance(result.dead_transitions, list)
        assert isinstance(result.missing_transitions, list)
        assert isinstance(result.errors, list)


class TestFSMAnalysisDeadTransitions:
    """Test detection of dead transitions (unreachable transitions)."""

    def test_detect_dead_transitions(self, base_version: ModelSemVer) -> None:
        """
        Test that transitions from unreachable states are detected as dead.

        If a transition's from_state is unreachable, the transition itself
        can never fire (dead transition).
        """
        states = [
            ModelFSMStateDefinition(
                version=base_version,
                state_name="idle",
                state_type="operational",
                description="Initial",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="reachable",
                state_type="operational",
                description="Reachable state",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="unreachable",
                state_type="operational",
                description="Unreachable state",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="completed",
                state_type="terminal",
                description="Terminal",
                is_terminal=True,
            ),
        ]

        transitions = [
            ModelFSMStateTransition(
                version=base_version,
                transition_name="start",
                from_state="idle",
                to_state="reachable",
                trigger="start",
                priority=1,
            ),
            ModelFSMStateTransition(
                version=base_version,
                transition_name="finish",
                from_state="reachable",
                to_state="completed",
                trigger="finish",
                priority=1,
            ),
            # Dead transition - from_state is unreachable
            ModelFSMStateTransition(
                version=base_version,
                transition_name="dead_transition",
                from_state="unreachable",
                to_state="completed",
                trigger="finish",
                priority=1,
            ),
        ]

        fsm = ModelFSMSubcontract(
            version=base_version,
            state_machine_name="DeadTransition",
            state_machine_version=base_version,
            description="FSM with dead transition",
            states=states,
            initial_state="idle",
            terminal_states=["completed"],
            transitions=transitions,
        )

        result = analyze_fsm(fsm)

        assert not result.is_valid, "FSM with dead transition should be invalid"
        assert len(result.dead_transitions) > 0, "Should detect dead transitions"
        assert "dead_transition" in result.dead_transitions


class TestFSMAnalysisEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimal_valid_fsm(self, base_version: ModelSemVer) -> None:
        """
        Test minimal valid FSM: initial → terminal.

        Simplest possible valid FSM should pass validation.
        """
        states = [
            ModelFSMStateDefinition(
                version=base_version,
                state_name="initial",
                state_type="operational",
                description="Initial state",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="terminal",
                state_type="terminal",
                description="Terminal state",
                is_terminal=True,
            ),
        ]

        transitions = [
            ModelFSMStateTransition(
                version=base_version,
                transition_name="complete",
                from_state="initial",
                to_state="terminal",
                trigger="finish",
                priority=1,
            ),
        ]

        fsm = ModelFSMSubcontract(
            version=base_version,
            state_machine_name="Minimal",
            state_machine_version=base_version,
            description="Minimal FSM",
            states=states,
            initial_state="initial",
            terminal_states=["terminal"],
            transitions=transitions,
        )

        result = analyze_fsm(fsm)

        assert result.is_valid, "Minimal FSM should be valid"
        assert len(result.unreachable_states) == 0
        assert len(result.cycles_without_exit) == 0

    def test_multiple_terminal_states(self, base_version: ModelSemVer) -> None:
        """
        Test FSM with multiple terminal states.

        FSM can have multiple valid endpoints (success, failure, etc.).
        """
        states = [
            ModelFSMStateDefinition(
                version=base_version,
                state_name="initial",
                state_type="operational",
                description="Initial",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="processing",
                state_type="operational",
                description="Processing",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="success",
                state_type="terminal",
                description="Success terminal",
                is_terminal=True,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="failure",
                state_type="terminal",
                description="Failure terminal",
                is_terminal=True,
            ),
        ]

        transitions = [
            ModelFSMStateTransition(
                version=base_version,
                transition_name="start",
                from_state="initial",
                to_state="processing",
                trigger="start",
                priority=1,
            ),
            ModelFSMStateTransition(
                version=base_version,
                transition_name="succeed",
                from_state="processing",
                to_state="success",
                trigger="complete",
                priority=1,
            ),
            ModelFSMStateTransition(
                version=base_version,
                transition_name="fail",
                from_state="processing",
                to_state="failure",
                trigger="error",
                priority=1,
            ),
        ]

        fsm = ModelFSMSubcontract(
            version=base_version,
            state_machine_name="MultipleTerminal",
            state_machine_version=base_version,
            description="FSM with multiple terminals",
            states=states,
            initial_state="initial",
            terminal_states=["success", "failure"],
            transitions=transitions,
        )

        result = analyze_fsm(fsm)

        assert result.is_valid, "FSM with multiple terminals should be valid"

    def test_self_loop_with_exit(self, base_version: ModelSemVer) -> None:
        """
        Test FSM with self-loop (state → itself) that also has exit.

        Self-loops are valid if there's also an exit path.
        """
        states = [
            ModelFSMStateDefinition(
                version=base_version,
                state_name="initial",
                state_type="operational",
                description="Initial",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="retry",
                state_type="operational",
                description="Retry state with self-loop",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                version=base_version,
                state_name="terminal",
                state_type="terminal",
                description="Terminal",
                is_terminal=True,
            ),
        ]

        transitions = [
            ModelFSMStateTransition(
                version=base_version,
                transition_name="start",
                from_state="initial",
                to_state="retry",
                trigger="start",
                priority=1,
            ),
            # Self-loop
            ModelFSMStateTransition(
                version=base_version,
                transition_name="retry_self",
                from_state="retry",
                to_state="retry",
                trigger="retry",
                priority=1,
            ),
            # Exit from self-loop
            ModelFSMStateTransition(
                version=base_version,
                transition_name="complete",
                from_state="retry",
                to_state="terminal",
                trigger="finish",
                priority=1,
            ),
        ]

        fsm = ModelFSMSubcontract(
            version=base_version,
            state_machine_name="SelfLoop",
            state_machine_version=base_version,
            description="FSM with self-loop and exit",
            states=states,
            initial_state="initial",
            terminal_states=["terminal"],
            transitions=transitions,
        )

        result = analyze_fsm(fsm)

        assert result.is_valid, "Self-loop with exit should be valid"
        assert len(result.cycles_without_exit) == 0
