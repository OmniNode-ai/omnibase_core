"""
Unit tests for MixinFSMExecution.

Tests the FSM execution mixin for declarative state machines.
"""

import pytest

from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
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


@pytest.fixture
def test_fsm() -> ModelFSMSubcontract:
    """Create test FSM contract."""
    return ModelFSMSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        state_machine_name="test_mixin_fsm",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test FSM for mixin",
        states=[
            ModelFSMStateDefinition(
                version=ModelSemVer(major=1, minor=0, patch=0),
                state_name="idle",
                state_type="operational",
                is_terminal=False,
                entry_actions=["log_idle"],
                description="Initial idle state",
            ),
            ModelFSMStateDefinition(
                version=ModelSemVer(major=1, minor=0, patch=0),
                state_name="running",
                state_type="operational",
                is_terminal=False,
                description="Running state",
            ),
            ModelFSMStateDefinition(
                version=ModelSemVer(major=1, minor=0, patch=0),
                state_name="completed",
                state_type="terminal",
                is_terminal=True,
                description="Terminal completion state",
            ),
        ],
        initial_state="idle",
        terminal_states=["completed"],
        error_states=[],
        transitions=[
            ModelFSMStateTransition(
                version=ModelSemVer(major=1, minor=0, patch=0),
                transition_name="start",
                from_state="idle",
                to_state="running",
                trigger="start",
                priority=1,
            ),
            ModelFSMStateTransition(
                version=ModelSemVer(major=1, minor=0, patch=0),
                transition_name="complete",
                from_state="running",
                to_state="completed",
                trigger="complete",
                priority=1,
            ),
        ],
        operations=[],
        persistence_enabled=True,
        recovery_enabled=True,
    )


class MockNode(MixinFSMExecution):
    """Mock node class using FSM mixin."""

    def __init__(self):
        """Initialize mock node."""
        super().__init__()


class TestMixinFSMExecution:
    """Test FSM execution mixin."""

    @pytest.mark.asyncio
    async def test_mixin_execute_transition(self, test_fsm: ModelFSMSubcontract):
        """Test executing transition through mixin."""
        node = MockNode()

        result = await node.execute_fsm_transition(
            test_fsm,
            trigger="start",
            context={"test": "data"},
        )

        assert result.success
        assert result.old_state == "idle"
        assert result.new_state == "running"

    @pytest.mark.asyncio
    async def test_mixin_state_tracking(self, test_fsm: ModelFSMSubcontract):
        """Test that mixin tracks current state."""
        node = MockNode()

        # Initially no state
        assert node.get_current_fsm_state() is None

        # Execute first transition
        await node.execute_fsm_transition(
            test_fsm,
            trigger="start",
            context={},
        )

        # Should be in running state now
        assert node.get_current_fsm_state() == "running"

        # Execute second transition
        await node.execute_fsm_transition(
            test_fsm,
            trigger="complete",
            context={},
        )

        # Should be in completed state now
        assert node.get_current_fsm_state() == "completed"

    @pytest.mark.asyncio
    async def test_mixin_history_tracking(self, test_fsm: ModelFSMSubcontract):
        """Test that mixin tracks state history."""
        node = MockNode()

        # Execute first transition
        await node.execute_fsm_transition(
            test_fsm,
            trigger="start",
            context={},
        )

        history = node.get_fsm_state_history()
        assert "idle" in history

        # Execute second transition
        await node.execute_fsm_transition(
            test_fsm,
            trigger="complete",
            context={},
        )

        history = node.get_fsm_state_history()
        assert "idle" in history
        assert "running" in history

    @pytest.mark.asyncio
    async def test_mixin_reset_state(self, test_fsm: ModelFSMSubcontract):
        """Test resetting FSM state."""
        node = MockNode()

        # Execute transition
        await node.execute_fsm_transition(
            test_fsm,
            trigger="start",
            context={},
        )

        assert node.get_current_fsm_state() == "running"

        # Reset
        node.reset_fsm_state(test_fsm)

        assert node.get_current_fsm_state() == "idle"
        assert node.get_fsm_state_history() == []

    @pytest.mark.asyncio
    async def test_mixin_initialize_state(self, test_fsm: ModelFSMSubcontract):
        """Test initializing FSM state with context."""
        node = MockNode()

        context = {"initial": "context", "batch_size": 100}
        node.initialize_fsm_state(test_fsm, context=context)

        assert node.get_current_fsm_state() == "idle"

    @pytest.mark.asyncio
    async def test_mixin_is_terminal_state(self, test_fsm: ModelFSMSubcontract):
        """Test checking for terminal state."""
        node = MockNode()

        # Initially not in terminal state
        node.initialize_fsm_state(test_fsm)
        assert not node.is_terminal_state(test_fsm)

        # Transition to running (not terminal)
        await node.execute_fsm_transition(
            test_fsm,
            trigger="start",
            context={},
        )
        assert not node.is_terminal_state(test_fsm)

        # Transition to completed (terminal)
        await node.execute_fsm_transition(
            test_fsm,
            trigger="complete",
            context={},
        )
        assert node.is_terminal_state(test_fsm)

    @pytest.mark.asyncio
    async def test_mixin_validate_contract(self, test_fsm: ModelFSMSubcontract):
        """Test validating FSM contract through mixin."""
        node = MockNode()

        errors = await node.validate_fsm_contract(test_fsm)
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_mixin_validate_invalid_contract(self):
        """Test validating invalid FSM contract."""
        node = MockNode()

        # Create invalid FSM using model_construct to bypass validators
        # (initial state doesn't exist in states list)
        invalid_fsm = ModelFSMSubcontract.model_construct(
            state_machine_name="invalid",
            state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Invalid FSM",
            states=[
                ModelFSMStateDefinition(
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    state_name="running",
                    state_type="operational",
                    is_terminal=False,
                    description="Running state",
                ),
            ],
            initial_state="idle",  # Doesn't exist!
            terminal_states=[],
            error_states=[],
            transitions=[
                # Add dummy transition to satisfy validation
                ModelFSMStateTransition(
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    transition_name="dummy",
                    from_state="running",
                    to_state="running",
                    trigger="dummy",
                    priority=1,
                ),
            ],
            operations=[],
            persistence_enabled=False,
            recovery_enabled=False,
        )

        errors = await node.validate_fsm_contract(invalid_fsm)
        assert len(errors) > 0
        assert any("Initial state not defined" in error for error in errors)

    @pytest.mark.asyncio
    async def test_mixin_failed_transition_doesnt_update_state(
        self, test_fsm: ModelFSMSubcontract
    ):
        """Test that failed transitions don't update mixin state."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        node = MockNode()
        node.initialize_fsm_state(test_fsm)

        # Try invalid transition - should raise ModelOnexError
        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_fsm_transition(
                test_fsm,
                trigger="invalid_trigger",
                context={},
            )

        # Verify the error message
        assert "invalid_trigger" in str(exc_info.value)

        # State should remain idle
        assert node.get_current_fsm_state() == "idle"
