"""
Unit tests for FSM execution utilities.

Tests the pure functions in utils/fsm_executor.py for FSM transition execution.
"""

from uuid import uuid4

import pytest

from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.contracts.subcontracts.model_fsmtransitionaction import (
    ModelFSMTransitionAction,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                is_terminal=False,
                entry_actions=["log_idle_entry"],
                exit_actions=["log_idle_exit"],
            ),
            ModelFSMStateDefinition(
                state_name="running",
                state_type="operational",
                is_terminal=False,
                entry_actions=["log_running_entry"],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="completed",
                state_type="terminal",
                is_terminal=True,
                entry_actions=["log_completion"],
                exit_actions=[],
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
            ),
            ModelFSMStateTransition(
                transition_name="complete",
                from_state="running",
                to_state="completed",
                trigger="complete_event",
                priority=1,
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
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                is_terminal=False,
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
                        expression="data_count min_length 1",
                        required=True,
                    )
                ],
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
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                is_terminal=False,
            ),
            ModelFSMStateDefinition(
                state_name="active",
                state_type="operational",
                is_terminal=False,
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
        context = {"data_count": [1, 2, 3]}  # Has data

        result = await execute_transition(fsm_with_conditions, "idle", "start", context)

        assert result.success
        assert result.new_state == "processing"

    @pytest.mark.asyncio
    async def test_condition_not_met(self, fsm_with_conditions: ModelFSMSubcontract):
        """Test transition when condition is not met."""
        context = {"data_count": []}  # Empty list

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
        context = {}  # No data_count field

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
        fsm = ModelFSMSubcontract(
            state_machine_name="invalid_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Invalid FSM",
            states=[
                ModelFSMStateDefinition(
                    state_name="running",
                    state_type="operational",
                    is_terminal=False,
                ),
            ],
            initial_state="idle",  # Doesn't exist!
            terminal_states=[],
            error_states=[],
            transitions=[],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        errors = await validate_fsm_contract(fsm)
        assert len(errors) > 0
        assert any("Initial state not defined" in error for error in errors)

    @pytest.mark.asyncio
    async def test_invalid_transition_states(self):
        """Test validation with transitions referencing non-existent states."""
        fsm = ModelFSMSubcontract(
            state_machine_name="invalid_transitions",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with invalid transitions",
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    is_terminal=False,
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
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        errors = await validate_fsm_contract(fsm)
        assert len(errors) > 0
        assert any(
            "Invalid target state" in error or "to_state" in error for error in errors
        )

    @pytest.mark.asyncio
    async def test_unreachable_states(self):
        """Test validation detects unreachable states."""
        fsm = ModelFSMSubcontract(
            state_machine_name="unreachable_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="FSM with unreachable states",
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    is_terminal=False,
                ),
                ModelFSMStateDefinition(
                    state_name="running",
                    state_type="operational",
                    is_terminal=False,
                ),
                ModelFSMStateDefinition(
                    state_name="orphan",  # Unreachable!
                    state_type="operational",
                    is_terminal=False,
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
        fsm = ModelFSMSubcontract(
            state_machine_name="broken_fsm",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Broken FSM",
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    is_terminal=False,
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
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await execute_transition(fsm, "idle", "go", {})

        assert "Invalid target state" in str(exc_info.value)


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
            states=[
                ModelFSMStateDefinition(
                    state_name="idle",
                    state_type="operational",
                    is_terminal=False,
                ),
                ModelFSMStateDefinition(
                    state_name="running",
                    state_type="operational",
                    is_terminal=False,
                ),
                ModelFSMStateDefinition(
                    state_name="error",
                    state_type="error",
                    is_terminal=True,
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
                ),
                ModelFSMStateTransition(
                    transition_name="error_handler",
                    from_state="*",  # Wildcard - from any state
                    to_state="error",
                    trigger="error",
                    priority=1,
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
            fsm_with_conditions, "idle", "start", {"data_count": [1, 2, 3]}
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
