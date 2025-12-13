"""
Unit tests for FSM execution utilities.

Tests the pure functions in utils/fsm_executor.py for FSM transition execution.
"""

import pytest

pytestmark = pytest.mark.unit

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
from omnibase_core.models.fsm.model_fsm_transition_action import (
    ModelFSMTransitionAction,
)
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.fsm_executor import (
    FSMState,
    execute_transition,
    get_initial_state,
    validate_fsm_contract,
)


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Create a simple FSM for testing."""
    return ModelFSMSubcontract(
        state_machine_name="test_fsm",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test FSM",
        version=ModelSemVer(major=1, minor=0, patch=0),
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Idle state - waiting for work",
                is_terminal=False,
                entry_actions=["log_idle_entry"],
                exit_actions=["log_idle_exit"],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="running",
                state_type="operational",
                description="Running state - actively processing",
                is_terminal=False,
                entry_actions=["log_running_entry"],
                exit_actions=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="completed",
                state_type="terminal",
                description="Completed state - processing finished",
                is_terminal=True,
                is_recoverable=False,  # Terminal states cannot be recoverable
                entry_actions=["log_completion"],
                exit_actions=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        initial_state="idle",
        terminal_states=["completed"],
        error_states=[],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="running",
                trigger="start_event",
                priority=1,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="complete",
                from_state="running",
                to_state="completed",
                trigger="complete_event",
                priority=1,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        operations=[],
        persistence_enabled=True,
        recovery_enabled=True,
    )


@pytest.fixture
def fsm_with_conditions() -> ModelFSMSubcontract:
    """Create FSM with conditional transitions."""
    return ModelFSMSubcontract(
        state_machine_name="conditional_fsm",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        description="FSM with conditions",
        version=ModelSemVer(major=1, minor=0, patch=0),
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Idle state with conditional transitions",
                is_terminal=False,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                description="Processing state with conditions",
                is_terminal=False,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        initial_state="idle",
        terminal_states=[],
        error_states=[],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start_processing",
                from_state="idle",
                to_state="processing",
                trigger="start",
                priority=1,
                conditions=[
                    ModelFSMTransitionCondition(
                        condition_name="has_data",
                        condition_type="field_check",
                        expression="data_count_len >= 1",
                        required=True,
                    )
                ],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )


@pytest.fixture
def fsm_with_actions() -> ModelFSMSubcontract:
    """Create FSM with transition actions."""
    return ModelFSMSubcontract(
        state_machine_name="action_fsm",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        description="FSM with actions",
        version=ModelSemVer(major=1, minor=0, patch=0),
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Idle state with transition actions",
                is_terminal=False,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="active",
                state_type="operational",
                description="Active state with resources initialized",
                is_terminal=False,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        initial_state="idle",
        terminal_states=[],
        error_states=[],
        transitions=[
            ModelFSMStateTransition(
                transition_name="activate",
                from_state="idle",
                to_state="active",
                trigger="activate",
                priority=1,
                actions=[
                    ModelFSMTransitionAction(
                        action_name="initialize_resources",
                        action_type="setup",
                        execution_order=1,
                        is_critical=True,
                    )
                ],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        operations=[],
        persistence_enabled=True,
        recovery_enabled=False,
    )


class TestFSMTransitionSuccess:
    """Test successful FSM transitions."""

    @pytest.mark.asyncio
    async def test_simple_transition_success(self, simple_fsm: ModelFSMSubcontract):
        """Test successful state transition."""
        result = await execute_transition(simple_fsm, "idle", "start_event", {})

        assert result.success
        assert result.old_state == "idle"
        assert result.new_state == "running"
        assert result.transition_name == "start"
        assert len(result.intents) > 0

        # Should have exit actions, transition actions, entry actions, persistence, and metrics
        intent_types = [intent.intent_type for intent in result.intents]
        assert "fsm_state_action" in intent_types  # Entry/exit actions
        assert "persist_state" in intent_types  # Persistence enabled
        assert "record_metric" in intent_types  # Metrics

    @pytest.mark.asyncio
    async def test_transition_to_terminal_state(self, simple_fsm: ModelFSMSubcontract):
        """Test transition to terminal state."""
        result = await execute_transition(simple_fsm, "running", "complete_event", {})

        assert result.success
        assert result.new_state == "completed"

        # Check for completion entry action
        action_intents = [
            i for i in result.intents if i.intent_type == "fsm_state_action"
        ]
        assert any("log_completion" in str(i.payload) for i in action_intents)

    @pytest.mark.asyncio
    async def test_entry_and_exit_actions(self, simple_fsm: ModelFSMSubcontract):
        """Test that entry and exit actions are emitted."""
        result = await execute_transition(simple_fsm, "idle", "start_event", {})

        action_intents = [
            i for i in result.intents if i.intent_type == "fsm_state_action"
        ]

        # Should have exit actions for "idle" and entry actions for "running"
        action_names = [i.payload.get("action_name") for i in action_intents]
        assert "log_idle_exit" in action_names
        assert "log_running_entry" in action_names

    @pytest.mark.asyncio
    async def test_transition_actions_executed(
        self, fsm_with_actions: ModelFSMSubcontract
    ):
        """Test that transition actions are emitted."""
        result = await execute_transition(fsm_with_actions, "idle", "activate", {})

        assert result.success

        transition_action_intents = [
            i for i in result.intents if i.intent_type == "fsm_transition_action"
        ]

        assert len(transition_action_intents) > 0
        assert any(
            "initialize_resources" in str(i.payload) for i in transition_action_intents
        )


class TestFSMConditions:
    """Test FSM transition conditions."""

    @pytest.mark.asyncio
    async def test_condition_met(self, fsm_with_conditions: ModelFSMSubcontract):
        """Test transition when condition is met."""
        context = {"data_count_len": 3}  # Has data (length >= 1)

        result = await execute_transition(fsm_with_conditions, "idle", "start", context)

        assert result.success
        assert result.new_state == "processing"

    @pytest.mark.asyncio
    async def test_condition_not_met(self, fsm_with_conditions: ModelFSMSubcontract):
        """Test transition when condition is not met."""
        context = {"data_count_len": 0}  # Empty (length < 1)

        result = await execute_transition(fsm_with_conditions, "idle", "start", context)

        assert not result.success
        assert result.new_state == "idle"  # Stays in current state
        assert result.error == "Transition conditions not met"

        # Should have warning log intent
        log_intents = [i for i in result.intents if i.intent_type == "log_event"]
        assert len(log_intents) > 0
        assert any("WARNING" in str(i.payload) for i in log_intents)

    @pytest.mark.asyncio
    async def test_condition_missing_field(
        self, fsm_with_conditions: ModelFSMSubcontract
    ):
        """Test transition when condition field is missing."""
        context = {}  # No data_count_len field

        result = await execute_transition(fsm_with_conditions, "idle", "start", context)

        assert not result.success
        assert result.new_state == "idle"


class TestFSMValidation:
    """Test FSM contract validation."""

    @pytest.mark.asyncio
    async def test_valid_fsm(self, simple_fsm: ModelFSMSubcontract):
        """Test validation of valid FSM."""
        errors = await validate_fsm_contract(simple_fsm)
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_invalid_initial_state(self):
        """Test validation with invalid initial state."""
        # ModelFSMSubcontract now validates at construction time
        with pytest.raises(ModelOnexError) as exc_info:
            fsm = ModelFSMSubcontract(
                state_machine_name="invalid_fsm",
                state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Invalid FSM",
                version=ModelSemVer(major=1, minor=0, patch=0),
                states=[
                    ModelFSMStateDefinition(
                        state_name="running",
                        state_type="operational",
                        description="Running state",
                        is_terminal=False,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                    ModelFSMStateDefinition(
                        state_name="completed",
                        state_type="terminal",
                        description="Completed state",
                        is_terminal=True,
                        is_recoverable=False,  # Terminal states cannot be recoverable
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                initial_state="idle",  # Doesn't exist!
                terminal_states=["completed"],
                error_states=[],
                transitions=[
                    ModelFSMStateTransition(
                        transition_name="complete",
                        from_state="running",
                        to_state="completed",
                        trigger="complete",
                        priority=1,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                operations=[],
                persistence_enabled=False,
                recovery_enabled=False,
            )

        assert "Initial state" in str(exc_info.value) and "idle" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_transition_states(self):
        """Test validation with transitions referencing non-existent states."""
        # ModelFSMSubcontract now validates at construction time
        with pytest.raises(ModelOnexError) as exc_info:
            fsm = ModelFSMSubcontract(
                state_machine_name="invalid_transitions",
                state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
                description="FSM with invalid transitions",
                version=ModelSemVer(major=1, minor=0, patch=0),
                states=[
                    ModelFSMStateDefinition(
                        state_name="idle",
                        state_type="operational",
                        description="Idle state",
                        is_terminal=False,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                initial_state="idle",
                terminal_states=[],
                error_states=[],
                transitions=[
                    ModelFSMStateTransition(
                        transition_name="invalid",
                        from_state="idle",
                        to_state="non_existent",  # Doesn't exist!
                        trigger="go",
                        priority=1,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                operations=[],
                persistence_enabled=False,
                recovery_enabled=False,
            )

        assert "to_state" in str(exc_info.value) or "non_existent" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_unreachable_states(self):
        """Test validation detects unreachable states."""
        fsm = ModelFSMSubcontract(
            state_machine_name="unreachable_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with unreachable states",
            version=ModelSemVer(major=1, minor=0, patch=0),
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    description="Idle state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="running",
                    state_type="operational",
                    description="Running state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="orphan",  # Unreachable!
                    state_type="operational",
                    description="Orphan state - unreachable",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            initial_state="idle",
            terminal_states=[],
            error_states=[],
            transitions=[
                ModelFSMStateTransition(
                    transition_name="start",
                    from_state="idle",
                    to_state="running",
                    trigger="start",
                    priority=1,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                # No transition to "orphan" state
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        errors = await validate_fsm_contract(fsm)
        assert len(errors) > 0
        assert any(
            "Unreachable states" in error and "orphan" in error for error in errors
        )

    @pytest.mark.asyncio
    async def test_terminal_state_explicit_transitions_blocked(self):
        """Test that terminal states cannot have explicit outgoing transitions.

        Terminal states should not have ANY explicit outgoing transitions,
        even to error states. Wildcard transitions (from_state="*") are
        naturally exempt as they don't originate from a specific terminal state.

        Note: This validation is now enforced at FSM construction time via
        Pydantic model validators, so we expect an exception to be raised
        when trying to create an FSM with transitions from terminal states.
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        with pytest.raises(ModelOnexError) as exc_info:
            ModelFSMSubcontract(
                state_machine_name="terminal_with_transition",
                state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
                description="FSM with terminal state having explicit outgoing transition",
                version=ModelSemVer(major=1, minor=0, patch=0),
                states=[
                    ModelFSMStateDefinition(
                        state_name="idle",
                        state_type="operational",
                        description="Idle state",
                        is_terminal=False,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                    ModelFSMStateDefinition(
                        state_name="completed",
                        state_type="terminal",
                        description="Completed state - should be terminal",
                        is_terminal=True,
                        is_recoverable=False,  # Terminal states cannot be recoverable
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                    ModelFSMStateDefinition(
                        state_name="error",
                        state_type="error",
                        description="Error state",
                        is_terminal=True,
                        is_recoverable=False,  # Terminal states cannot be recoverable
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                initial_state="idle",
                terminal_states=["completed"],
                error_states=["error"],
                transitions=[
                    ModelFSMStateTransition(
                        transition_name="complete",
                        from_state="idle",
                        to_state="completed",
                        trigger="complete",
                        priority=1,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                    ModelFSMStateTransition(
                        transition_name="error_from_terminal",
                        from_state="completed",  # Explicit transition from terminal state
                        to_state="error",
                        trigger="error",
                        priority=1,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                operations=[],
                persistence_enabled=False,
                recovery_enabled=False,
            )

        # Verify the error message mentions terminal state transitions
        error_message = str(exc_info.value)
        assert "terminal" in error_message.lower() or "completed" in error_message

    @pytest.mark.asyncio
    async def test_wildcard_transitions_allowed_from_terminal(self):
        """Test that wildcard transitions are allowed even when terminal states exist.

        Wildcard transitions (from_state="*") should work from any state including
        terminal states, as they don't represent explicit outgoing transitions from
        terminal states.
        """
        fsm = ModelFSMSubcontract(
            state_machine_name="wildcard_with_terminal",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with wildcard transition and terminal state",
            version=ModelSemVer(major=1, minor=0, patch=0),
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    description="Idle state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="completed",
                    state_type="terminal",
                    description="Completed state - terminal",
                    is_terminal=True,
                    is_recoverable=False,  # Terminal states cannot be recoverable
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="error",
                    state_type="error",
                    description="Error state",
                    is_terminal=True,
                    is_recoverable=False,  # Terminal states cannot be recoverable
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            initial_state="idle",
            terminal_states=["completed"],
            error_states=["error"],
            transitions=[
                ModelFSMStateTransition(
                    transition_name="complete",
                    from_state="idle",
                    to_state="completed",
                    trigger="complete",
                    priority=1,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateTransition(
                    transition_name="wildcard_error_handler",
                    from_state="*",  # Wildcard - applies to all states
                    to_state="error",
                    trigger="error",
                    priority=1,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        # Should have no validation errors - wildcard transitions are allowed
        errors = await validate_fsm_contract(fsm)
        assert len(errors) == 0


class TestFSMErrors:
    """Test FSM error handling."""

    @pytest.mark.asyncio
    async def test_invalid_current_state(self, simple_fsm: ModelFSMSubcontract):
        """Test transition from invalid current state."""
        with pytest.raises(ModelOnexError) as exc_info:
            await execute_transition(simple_fsm, "non_existent", "start_event", {})

        assert "Invalid current state" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_trigger(self, simple_fsm: ModelFSMSubcontract):
        """Test transition with invalid trigger."""
        with pytest.raises(ModelOnexError) as exc_info:
            await execute_transition(simple_fsm, "idle", "invalid_trigger", {})

        assert "No transition" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_target_state(self):
        """Test transition with invalid target state in definition."""
        # ModelFSMSubcontract now validates at construction time
        with pytest.raises(ModelOnexError) as exc_info:
            fsm = ModelFSMSubcontract(
                state_machine_name="broken_fsm",
                state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
                description="Broken FSM",
                version=ModelSemVer(major=1, minor=0, patch=0),
                states=[
                    ModelFSMStateDefinition(
                        state_name="idle",
                        state_type="operational",
                        description="Idle state",
                        is_terminal=False,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                initial_state="idle",
                terminal_states=[],
                error_states=[],
                transitions=[
                    ModelFSMStateTransition(
                        transition_name="broken",
                        from_state="idle",
                        to_state="non_existent",  # Target doesn't exist
                        trigger="go",
                        priority=1,
                        version=ModelSemVer(major=1, minor=0, patch=0),
                    ),
                ],
                operations=[],
                persistence_enabled=False,
                recovery_enabled=False,
            )

        assert "to_state" in str(exc_info.value) or "non_existent" in str(
            exc_info.value
        )


class TestFSMState:
    """Test FSM state management."""

    def test_get_initial_state(self, simple_fsm: ModelFSMSubcontract):
        """Test getting initial state."""
        state = get_initial_state(simple_fsm)

        assert isinstance(state, FSMState)
        assert state.current_state == "idle"
        assert state.context == {}
        assert state.history == []

    def test_fsm_state_creation(self):
        """Test FSM state creation with context."""
        state = FSMState(
            current_state="running",
            context={"data": [1, 2, 3]},
            history=["idle"],
        )

        assert state.current_state == "running"
        assert state.context["data"] == [1, 2, 3]
        assert state.history == ["idle"]


class TestWildcardTransitions:
    """Test wildcard transitions (from any state)."""

    @pytest.mark.asyncio
    async def test_wildcard_transition(self):
        """Test transition with wildcard from_state."""
        fsm = ModelFSMSubcontract(
            state_machine_name="wildcard_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with wildcard",
            version=ModelSemVer(major=1, minor=0, patch=0),
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    description="Idle state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="running",
                    state_type="operational",
                    description="Running state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="error",
                    state_type="error",
                    description="Error state - terminal",
                    is_terminal=True,
                    is_recoverable=False,  # Terminal states cannot be recoverable
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            initial_state="idle",
            terminal_states=[],
            error_states=["error"],
            transitions=[
                ModelFSMStateTransition(
                    transition_name="start",
                    from_state="idle",
                    to_state="running",
                    trigger="start",
                    priority=1,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateTransition(
                    transition_name="error_handler",
                    from_state="*",  # Wildcard - from any state
                    to_state="error",
                    trigger="error",
                    priority=1,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        # Test error transition from idle
        result = await execute_transition(fsm, "idle", "error", {})
        assert result.success
        assert result.new_state == "error"

        # Test error transition from running
        result = await execute_transition(fsm, "running", "error", {})
        assert result.success
        assert result.new_state == "error"


class TestPersistenceIntents:
    """Test persistence intent emission."""

    @pytest.mark.asyncio
    async def test_persistence_intent_emitted_when_enabled(
        self, simple_fsm: ModelFSMSubcontract
    ):
        """Test that persistence intents are emitted when enabled."""
        assert simple_fsm.persistence_enabled

        result = await execute_transition(simple_fsm, "idle", "start_event", {})

        persist_intents = [
            i for i in result.intents if i.intent_type == "persist_state"
        ]
        assert len(persist_intents) == 1

        persist_intent = persist_intents[0]
        assert persist_intent.target == "state_persistence"
        assert persist_intent.payload["fsm_name"] == "test_fsm"
        assert persist_intent.payload["state"] == "running"
        assert persist_intent.payload["previous_state"] == "idle"

    @pytest.mark.asyncio
    async def test_no_persistence_intent_when_disabled(
        self, fsm_with_conditions: ModelFSMSubcontract
    ):
        """Test that persistence intents are not emitted when disabled."""
        assert not fsm_with_conditions.persistence_enabled

        result = await execute_transition(
            fsm_with_conditions, "idle", "start", {"data_count_len": 3}
        )

        persist_intents = [
            i for i in result.intents if i.intent_type == "persist_state"
        ]
        assert len(persist_intents) == 0


class TestMetricsIntents:
    """Test metrics intent emission."""

    @pytest.mark.asyncio
    async def test_metrics_intent_always_emitted(self, simple_fsm: ModelFSMSubcontract):
        """Test that metrics intents are always emitted."""
        result = await execute_transition(simple_fsm, "idle", "start_event", {})

        metric_intents = [i for i in result.intents if i.intent_type == "record_metric"]
        assert len(metric_intents) == 1

        metric_intent = metric_intents[0]
        assert metric_intent.target == "metrics_service"
        assert metric_intent.payload["metric_name"] == "fsm_transition"
        assert metric_intent.payload["tags"]["fsm"] == "test_fsm"
        assert metric_intent.payload["tags"]["from_state"] == "idle"
        assert metric_intent.payload["tags"]["to_state"] == "running"


class TestNestedFieldAccess:
    """Test nested field access in FSM condition expressions."""

    @pytest.fixture
    def fsm_with_nested_conditions(self) -> ModelFSMSubcontract:
        """Create FSM with conditions using nested field paths."""
        return ModelFSMSubcontract(
            state_machine_name="nested_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with nested field conditions",
            version=ModelSemVer(major=1, minor=0, patch=0),
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    description="Idle state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="active",
                    state_type="operational",
                    description="Active state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            initial_state="idle",
            terminal_states=[],
            error_states=[],
            transitions=[
                ModelFSMStateTransition(
                    transition_name="activate_with_nested",
                    from_state="idle",
                    to_state="active",
                    trigger="activate",
                    priority=1,
                    conditions=[
                        ModelFSMTransitionCondition(
                            condition_name="check_user_email",
                            condition_type="field_check",
                            expression="user.email == test@example.com",
                            required=True,
                        )
                    ],
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

    @pytest.mark.asyncio
    async def test_nested_field_condition_met(
        self, fsm_with_nested_conditions: ModelFSMSubcontract
    ):
        """Test transition when nested field condition is met."""
        context = {"user": {"email": "test@example.com", "name": "Test User"}}

        result = await execute_transition(
            fsm_with_nested_conditions, "idle", "activate", context
        )

        assert result.success
        assert result.new_state == "active"

    @pytest.mark.asyncio
    async def test_nested_field_condition_not_met(
        self, fsm_with_nested_conditions: ModelFSMSubcontract
    ):
        """Test transition when nested field condition is not met."""
        context = {"user": {"email": "wrong@example.com", "name": "Test User"}}

        result = await execute_transition(
            fsm_with_nested_conditions, "idle", "activate", context
        )

        assert not result.success
        assert result.new_state == "idle"
        assert result.error == "Transition conditions not met"

    @pytest.mark.asyncio
    async def test_nested_field_missing_parent(
        self, fsm_with_nested_conditions: ModelFSMSubcontract
    ):
        """Test transition when parent of nested field is missing."""
        context = {"other_data": "value"}  # No 'user' key

        result = await execute_transition(
            fsm_with_nested_conditions, "idle", "activate", context
        )

        assert not result.success
        assert result.new_state == "idle"

    @pytest.mark.asyncio
    async def test_nested_field_missing_child(
        self, fsm_with_nested_conditions: ModelFSMSubcontract
    ):
        """Test transition when nested field itself is missing."""
        context = {"user": {"name": "Test User"}}  # No 'email' key

        result = await execute_transition(
            fsm_with_nested_conditions, "idle", "activate", context
        )

        assert not result.success
        assert result.new_state == "idle"

    @pytest.mark.asyncio
    async def test_nested_field_parent_is_none(
        self, fsm_with_nested_conditions: ModelFSMSubcontract
    ):
        """Test transition when parent is None."""
        context = {"user": None}

        result = await execute_transition(
            fsm_with_nested_conditions, "idle", "activate", context
        )

        assert not result.success
        assert result.new_state == "idle"

    @pytest.mark.asyncio
    async def test_deeply_nested_field(self):
        """Test access to deeply nested fields (3+ levels)."""
        fsm = ModelFSMSubcontract(
            state_machine_name="deep_nested_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with deeply nested conditions",
            version=ModelSemVer(major=1, minor=0, patch=0),
            states=[
                ModelFSMStateDefinition(
                    state_name="start",
                    state_type="operational",
                    description="Start state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="end",
                    state_type="operational",
                    description="End state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            initial_state="start",
            terminal_states=[],
            error_states=[],
            transitions=[
                ModelFSMStateTransition(
                    transition_name="check_deep",
                    from_state="start",
                    to_state="end",
                    trigger="go",
                    priority=1,
                    conditions=[
                        ModelFSMTransitionCondition(
                            condition_name="deep_check",
                            condition_type="field_check",
                            expression="config.settings.feature.enabled == true",
                            required=True,
                        )
                    ],
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        context = {
            "config": {
                "settings": {"feature": {"enabled": "true", "name": "test_feature"}}
            }
        }

        result = await execute_transition(fsm, "start", "go", context)

        assert result.success
        assert result.new_state == "end"


class TestExpressionValidation:
    """Test expression validation using parse_expression."""

    @pytest.fixture
    def fsm_for_expression_tests(self) -> ModelFSMSubcontract:
        """Create a basic FSM for expression tests."""
        return ModelFSMSubcontract(
            state_machine_name="expr_test_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM for expression validation tests",
            version=ModelSemVer(major=1, minor=0, patch=0),
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    description="Idle state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                ModelFSMStateDefinition(
                    state_name="active",
                    state_type="operational",
                    description="Active state",
                    is_terminal=False,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            initial_state="idle",
            terminal_states=[],
            error_states=[],
            transitions=[
                # Dummy transition to satisfy min_length=1 validation
                ModelFSMStateTransition(
                    transition_name="dummy_transition",
                    from_state="idle",
                    to_state="active",
                    trigger="dummy",
                    priority=1,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

    @pytest.mark.asyncio
    async def test_invalid_expression_underscore_field(
        self, fsm_for_expression_tests: ModelFSMSubcontract
    ):
        """Test that underscore-prefixed fields are rejected for security."""
        # Create new FSM with transition containing underscore-prefixed field (security risk)
        # Note: ModelFSMSubcontract is frozen, so we use model_copy instead of append
        unsafe_transition = ModelFSMStateTransition(
            transition_name="unsafe_check",
            from_state="idle",
            to_state="active",
            trigger="go",
            priority=1,
            conditions=[
                ModelFSMTransitionCondition(
                    condition_name="private_field_check",
                    condition_type="field_check",
                    expression="_private_field equals secret",
                    required=True,
                )
            ],
            version=ModelSemVer(major=1, minor=0, patch=0),
        )
        fsm_with_unsafe_transition = fsm_for_expression_tests.model_copy(
            update={
                "transitions": [
                    *fsm_for_expression_tests.transitions,
                    unsafe_transition,
                ]
            }
        )

        context = {"_private_field": "secret"}

        # Should fail because underscore-prefixed fields are rejected
        result = await execute_transition(
            fsm_with_unsafe_transition, "idle", "go", context
        )

        assert not result.success
        assert result.new_state == "idle"

    @pytest.mark.asyncio
    async def test_invalid_expression_nested_underscore_field(
        self, fsm_for_expression_tests: ModelFSMSubcontract
    ):
        """Test that nested underscore-prefixed fields are rejected."""
        # Create new FSM with transition containing nested underscore field
        # Note: ModelFSMSubcontract is frozen, so we use model_copy instead of append
        nested_unsafe_transition = ModelFSMStateTransition(
            transition_name="nested_unsafe_check",
            from_state="idle",
            to_state="active",
            trigger="go",
            priority=1,
            conditions=[
                ModelFSMTransitionCondition(
                    condition_name="nested_private_check",
                    condition_type="field_check",
                    expression="user._internal equals value",
                    required=True,
                )
            ],
            version=ModelSemVer(major=1, minor=0, patch=0),
        )
        fsm_with_nested_unsafe = fsm_for_expression_tests.model_copy(
            update={
                "transitions": [
                    *fsm_for_expression_tests.transitions,
                    nested_unsafe_transition,
                ]
            }
        )

        context = {"user": {"_internal": "value"}}

        # Should fail because nested underscore-prefixed fields are rejected
        result = await execute_transition(fsm_with_nested_unsafe, "idle", "go", context)

        assert not result.success
        assert result.new_state == "idle"

    @pytest.mark.asyncio
    async def test_expression_with_symbolic_operators(
        self, fsm_for_expression_tests: ModelFSMSubcontract
    ):
        """Test that symbolic operators (>=, <=, etc.) work correctly."""
        # Create new FSM with transition using symbolic operators
        # Note: ModelFSMSubcontract is frozen, so we use model_copy instead of append
        symbolic_transition = ModelFSMStateTransition(
            transition_name="symbolic_check",
            from_state="idle",
            to_state="active",
            trigger="go",
            priority=1,
            conditions=[
                ModelFSMTransitionCondition(
                    condition_name="count_check",
                    condition_type="field_check",
                    expression="count >= 5",
                    required=True,
                )
            ],
            version=ModelSemVer(major=1, minor=0, patch=0),
        )
        fsm_with_symbolic = fsm_for_expression_tests.model_copy(
            update={
                "transitions": [
                    *fsm_for_expression_tests.transitions,
                    symbolic_transition,
                ]
            }
        )

        # Test with condition met
        context = {"count": 10}
        result = await execute_transition(fsm_with_symbolic, "idle", "go", context)
        assert result.success
        assert result.new_state == "active"

    @pytest.mark.asyncio
    async def test_expression_with_textual_operators(
        self, fsm_for_expression_tests: ModelFSMSubcontract
    ):
        """Test that textual operators (equals, not_equals, etc.) work correctly."""
        # Create new FSM with transition using textual operators
        # Note: ModelFSMSubcontract is frozen, so we use model_copy instead of append
        textual_transition = ModelFSMStateTransition(
            transition_name="textual_check",
            from_state="idle",
            to_state="active",
            trigger="go",
            priority=1,
            conditions=[
                ModelFSMTransitionCondition(
                    condition_name="status_check",
                    condition_type="field_check",
                    expression="status equals ready",
                    required=True,
                )
            ],
            version=ModelSemVer(major=1, minor=0, patch=0),
        )
        fsm_with_textual = fsm_for_expression_tests.model_copy(
            update={
                "transitions": [
                    *fsm_for_expression_tests.transitions,
                    textual_transition,
                ]
            }
        )

        context = {"status": "ready"}
        result = await execute_transition(fsm_with_textual, "idle", "go", context)
        assert result.success
        assert result.new_state == "active"
