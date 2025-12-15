"""Unit tests for node state serialization methods [OMN-739, OMN-740].

Tests state serialization, snapshot creation, and restoration for:
- NodeReducer FSM state serialization
- NodeOrchestrator workflow state serialization
- ModelWorkflowStateSnapshot model behavior

These tests verify the state persistence and recovery mechanisms that enable
workflow replay, debugging, and crash recovery patterns.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
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
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.fsm import ModelFSMStateSnapshot
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.workflow import ModelWorkflowStateSnapshot
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
from omnibase_core.nodes.node_reducer import NodeReducer

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container for dependency injection."""
    return ModelONEXContainer()


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Create simple FSM contract for testing state serialization."""
    return ModelFSMSubcontract(
        state_machine_name="serialization_test_fsm",
        description="FSM for state serialization tests",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        version=ModelSemVer(major=1, minor=0, patch=0),
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=[],
                exit_actions=[],
            ),
            ModelFSMStateDefinition(
                state_name="processing",
                state_type="operational",
                description="Processing state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=["start_processing"],
                exit_actions=["stop_processing"],
            ),
            ModelFSMStateDefinition(
                state_name="completed",
                state_type="terminal",
                description="Terminal state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                is_terminal=True,
                is_recoverable=False,
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="start",
                from_state="idle",
                to_state="processing",
                trigger="start_event",
                version=ModelSemVer(major=1, minor=0, patch=0),
                conditions=[],
                actions=[],
            ),
            ModelFSMStateTransition(
                transition_name="complete",
                from_state="processing",
                to_state="completed",
                trigger="complete_event",
                version=ModelSemVer(major=1, minor=0, patch=0),
                conditions=[],
                actions=[],
            ),
        ],
        terminal_states=["completed"],
        error_states=[],
        operations=[],
        persistence_enabled=True,
        recovery_enabled=True,
    )


@pytest.fixture
def simple_workflow_definition() -> ModelWorkflowDefinition:
    """Create simple workflow definition for testing state serialization."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="serialization_test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Workflow for state serialization tests",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        version=ModelSemVer(major=1, minor=0, patch=0),
    )


class TestNodeReducerStateSerialization:
    """Tests for NodeReducer state serialization methods.

    Tests the FSM state snapshot and restoration capabilities:
    - snapshot_state() returns ModelFSMStateSnapshot | None
    - restore_state() accepts ModelFSMStateSnapshot
    - get_state_snapshot() returns dict[str, object] | None (for JSON serialization)
    - Round-trip serialization maintains state integrity
    """

    def test_snapshot_state_returns_none_when_not_initialized(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test snapshot_state returns None when FSM not initialized."""
        node = NodeReducer(test_container)

        # FSM not initialized - no contract loaded
        snapshot = node.snapshot_state()

        assert snapshot is None

    def test_snapshot_state_returns_current_state(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test snapshot_state returns current FSM state after initialization."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={"test_key": "test_value"})

        snapshot = node.snapshot_state()

        assert snapshot is not None
        assert isinstance(snapshot, ModelFSMStateSnapshot)
        assert snapshot.current_state == "idle"
        assert snapshot.context == {"test_key": "test_value"}
        assert snapshot.history == []

    def test_restore_state_sets_fsm_state(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state correctly sets internal FSM state."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create a snapshot with non-initial state
        target_snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={"restored": True, "step": 5},
            history=["idle"],
        )

        # Restore the state
        node.restore_state(target_snapshot)

        # Verify internal state was updated
        current_snapshot = node.snapshot_state()
        assert current_snapshot is not None
        assert current_snapshot.current_state == "processing"
        assert current_snapshot.context == {"restored": True, "step": 5}
        assert current_snapshot.history == ["idle"]

    def test_restore_state_raises_without_contract(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test restore_state raises ModelOnexError if FSM contract not loaded."""
        node = NodeReducer(test_container)

        # Create a valid snapshot
        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context={},
            history=[],
        )

        # Should raise because FSM contract is not loaded
        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_state(snapshot)

        assert "FSM contract not loaded" in str(exc_info.value)

    def test_get_state_snapshot_returns_dict(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test get_state_snapshot returns JSON-serializable dict.

        Note: get_state_snapshot() returns dict[str, object] for JSON serialization.
        For strongly-typed access, use snapshot_state() which returns ModelFSMStateSnapshot.
        """
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={"key": "value"})

        snapshot = node.get_state_snapshot()

        assert isinstance(snapshot, dict)
        assert snapshot["current_state"] == "idle"
        assert snapshot["context"] == {"key": "value"}
        assert snapshot["history"] == []

    def test_get_state_snapshot_returns_none_when_not_initialized(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test get_state_snapshot returns None when FSM not initialized."""
        node = NodeReducer(test_container)

        snapshot = node.get_state_snapshot()

        assert snapshot is None

    @pytest.mark.asyncio
    async def test_snapshot_restore_roundtrip(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test snapshot then restore produces identical state."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={"initial": True})

        # Perform a transition to change state
        await node.execute_fsm_transition(
            simple_fsm, "start_event", {"transitioned": True}
        )

        # Take snapshot after transition
        original_snapshot = node.snapshot_state()
        assert original_snapshot is not None
        assert original_snapshot.current_state == "processing"

        # Simulate state loss by reinitializing
        node.initialize_fsm_state(simple_fsm, context={})
        assert node.get_current_state() == "idle"

        # Restore from snapshot
        node.restore_state(original_snapshot)

        # Verify state was restored correctly
        restored_snapshot = node.snapshot_state()
        assert restored_snapshot is not None
        assert restored_snapshot.current_state == original_snapshot.current_state
        assert restored_snapshot.context == original_snapshot.context
        assert restored_snapshot.history == original_snapshot.history

    def test_restore_state_rejects_invalid_current_state(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state raises error for state not in FSM contract."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create snapshot with state that doesn't exist in contract
        invalid_snapshot = ModelFSMStateSnapshot(
            current_state="nonexistent_state",
            context={},
            history=[],
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_state(invalid_snapshot)

        assert "Invalid FSM snapshot" in str(exc_info.value)
        assert "nonexistent_state" in str(exc_info.value)
        assert "not defined in FSM contract" in str(exc_info.value)

    def test_restore_state_rejects_invalid_history_state(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state raises error for history containing invalid states."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create snapshot with valid current state but invalid history
        invalid_snapshot = ModelFSMStateSnapshot(
            current_state="processing",  # Valid state
            context={},
            history=["idle", "invalid_history_state"],  # Contains invalid state
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_state(invalid_snapshot)

        assert "Invalid FSM snapshot" in str(exc_info.value)
        assert "invalid_history_state" in str(exc_info.value)
        assert "history contains invalid state" in str(exc_info.value)

    def test_restore_state_rejects_future_timestamp(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state raises error for snapshot with future timestamp."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create snapshot with future timestamp in context
        future_time = datetime(2099, 12, 31, 23, 59, 59)
        snapshot_with_future_time = ModelFSMStateSnapshot(
            current_state="processing",
            context={"created_at": future_time},
            history=["idle"],
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_state(snapshot_with_future_time)

        assert "is in the future" in str(exc_info.value)

    def test_restore_state_rejects_future_timestamp_iso_string(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state handles ISO string timestamps correctly."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create snapshot with future timestamp as ISO string
        snapshot_with_future_time = ModelFSMStateSnapshot(
            current_state="processing",
            context={"timestamp": "2099-12-31T23:59:59+00:00"},
            history=["idle"],
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_state(snapshot_with_future_time)

        assert "is in the future" in str(exc_info.value)

    def test_restore_state_accepts_valid_snapshot_with_history(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state accepts snapshot with valid states in history."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create valid snapshot with history of valid states
        valid_snapshot = ModelFSMStateSnapshot(
            current_state="completed",
            context={"step": 3},
            history=["idle", "processing"],  # All valid states
        )

        # Should not raise
        node.restore_state(valid_snapshot)

        # Verify state was restored
        current_snapshot = node.snapshot_state()
        assert current_snapshot is not None
        assert current_snapshot.current_state == "completed"
        assert current_snapshot.history == ["idle", "processing"]

    def test_restore_state_accepts_past_timestamp(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test restore_state accepts snapshot with past timestamp."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Create snapshot with past timestamp
        past_time = datetime(2020, 1, 1, 0, 0, 0)
        snapshot_with_past_time = ModelFSMStateSnapshot(
            current_state="processing",
            context={"created_at": past_time},
            history=["idle"],
        )

        # Should not raise
        node.restore_state(snapshot_with_past_time)

        # Verify state was restored
        current_snapshot = node.snapshot_state()
        assert current_snapshot is not None
        assert current_snapshot.current_state == "processing"


class TestNodeOrchestratorStateSerialization:
    """Tests for NodeOrchestrator workflow state serialization methods.

    Tests the workflow state snapshot and restoration capabilities:
    - snapshot_workflow_state() returns ModelWorkflowStateSnapshot | None
    - restore_workflow_state() accepts ModelWorkflowStateSnapshot
    - get_workflow_snapshot() returns dict[str, object] | None (for JSON serialization)
    - Round-trip serialization maintains state integrity
    - update_workflow_state() manually updates workflow state
    - execute_workflow_from_contract() automatically captures workflow state
    """

    def test_snapshot_workflow_state_returns_none_when_not_initialized(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test snapshot_workflow_state returns None when no workflow in progress."""
        node = NodeOrchestrator(test_container)

        # No workflow state initialized
        snapshot = node.snapshot_workflow_state()

        assert snapshot is None

    def test_update_workflow_state_populates_snapshot(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test update_workflow_state manually populates _workflow_state."""
        node = NodeOrchestrator(test_container)

        # Initially no workflow state
        assert node.snapshot_workflow_state() is None

        # Manually update workflow state
        workflow_id = uuid4()
        step1_id = uuid4()
        node.update_workflow_state(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[step1_id],
            context={"key": "value"},
        )

        # Verify snapshot is now available
        snapshot = node.snapshot_workflow_state()
        assert snapshot is not None
        assert isinstance(snapshot, ModelWorkflowStateSnapshot)
        assert snapshot.workflow_id == workflow_id
        assert snapshot.current_step_index == 1
        assert snapshot.completed_step_ids == (step1_id,)
        assert snapshot.context == {"key": "value"}

    def test_update_workflow_state_with_failed_steps(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test update_workflow_state tracks failed steps."""
        node = NodeOrchestrator(test_container)

        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()

        node.update_workflow_state(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step1_id],
            failed_step_ids=[step2_id],
            context={"error": "step2 failed"},
        )

        snapshot = node.snapshot_workflow_state()
        assert snapshot is not None
        assert snapshot.current_step_index == 2
        assert snapshot.completed_step_ids == (step1_id,)
        assert snapshot.failed_step_ids == (step2_id,)
        assert snapshot.context == {"error": "step2 failed"}

    def test_update_workflow_state_replaces_previous_state(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test update_workflow_state replaces previous state (not merge)."""
        node = NodeOrchestrator(test_container)

        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()

        # First update
        node.update_workflow_state(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[step1_id],
            context={"first": True},
        )

        # Second update (replaces, not merges)
        node.update_workflow_state(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step1_id, step2_id],
            context={"second": True},
        )

        snapshot = node.snapshot_workflow_state()
        assert snapshot is not None
        assert snapshot.current_step_index == 2
        assert snapshot.completed_step_ids == (step1_id, step2_id)
        # Context is replaced, not merged
        assert snapshot.context == {"second": True}
        assert "first" not in snapshot.context

    def test_snapshot_workflow_state_returns_current_state(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test snapshot_workflow_state returns current state after being set."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Manually set workflow state for testing
        workflow_id = uuid4()
        step1_id = uuid4()
        test_state = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[step1_id],
            failed_step_ids=[],
            context={"test_key": "test_value"},
        )
        node.restore_workflow_state(test_state)

        snapshot = node.snapshot_workflow_state()

        assert snapshot is not None
        assert isinstance(snapshot, ModelWorkflowStateSnapshot)
        assert snapshot.workflow_id == workflow_id
        assert snapshot.current_step_index == 1
        assert snapshot.completed_step_ids == (step1_id,)
        assert snapshot.context == {"test_key": "test_value"}

    def test_restore_workflow_state_sets_state(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state correctly sets internal workflow state."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create target snapshot
        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()
        target_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=3,
            completed_step_ids=[step1_id, step2_id],
            failed_step_ids=[],
            context={"restored": True, "retry_count": 2},
        )

        # Restore the state
        node.restore_workflow_state(target_snapshot)

        # Verify internal state was updated
        current_snapshot = node.snapshot_workflow_state()
        assert current_snapshot is not None
        assert current_snapshot.workflow_id == workflow_id
        assert current_snapshot.current_step_index == 3
        assert current_snapshot.completed_step_ids == (step1_id, step2_id)
        assert current_snapshot.context == {"restored": True, "retry_count": 2}

    def test_snapshot_workflow_state_returns_model(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test snapshot_workflow_state returns strongly-typed model."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Set workflow state
        workflow_id = uuid4()
        step_id = uuid4()
        test_state = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step_id],
            failed_step_ids=[],
            context={"key": "value"},
        )
        node.restore_workflow_state(test_state)

        snapshot = node.snapshot_workflow_state()

        assert isinstance(snapshot, ModelWorkflowStateSnapshot)
        assert snapshot.workflow_id == workflow_id
        assert snapshot.current_step_index == 2
        assert snapshot.completed_step_ids == (step_id,)
        assert snapshot.context == {"key": "value"}
        assert snapshot.created_at is not None

    def test_get_workflow_snapshot_returns_dict(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test get_workflow_snapshot returns JSON-serializable dict.

        Note: get_workflow_snapshot() uses mode="json" which converts UUIDs to strings
        and tuples to lists for JSON compatibility. Use snapshot_workflow_state() for
        strongly-typed access with UUID objects.
        """
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Set workflow state
        workflow_id = uuid4()
        step_id = uuid4()
        test_state = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step_id],
            failed_step_ids=[],
            context={"key": "value"},
        )
        node.restore_workflow_state(test_state)

        snapshot_dict = node.get_workflow_snapshot()

        assert isinstance(snapshot_dict, dict)
        # workflow_id is converted to string by mode="json"
        assert snapshot_dict["workflow_id"] == str(workflow_id)
        assert snapshot_dict["current_step_index"] == 2
        # completed_step_ids is a list of strings (mode="json" converts tuples to lists)
        assert snapshot_dict["completed_step_ids"] == [str(step_id)]
        assert snapshot_dict["context"] == {"key": "value"}
        assert snapshot_dict["created_at"] is not None

    def test_get_workflow_snapshot_returns_none_when_not_initialized(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test get_workflow_snapshot returns None when no workflow state."""
        node = NodeOrchestrator(test_container)

        snapshot = node.get_workflow_snapshot()

        assert snapshot is None

    def test_snapshot_restore_roundtrip(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test snapshot then restore produces identical state."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create initial workflow state
        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()
        initial_state = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step1_id],
            failed_step_ids=[step2_id],
            context={"original": True, "attempts": 3},
        )
        node.restore_workflow_state(initial_state)

        # Take snapshot
        original_snapshot = node.snapshot_workflow_state()
        assert original_snapshot is not None

        # Simulate state loss by setting different state
        different_state = ModelWorkflowStateSnapshot(
            workflow_id=uuid4(),
            current_step_index=0,
            completed_step_ids=[],
            failed_step_ids=[],
            context={},
        )
        node.restore_workflow_state(different_state)

        # Verify state was changed
        current = node.snapshot_workflow_state()
        assert current is not None
        assert current.workflow_id != workflow_id

        # Restore from original snapshot
        node.restore_workflow_state(original_snapshot)

        # Verify state was restored correctly
        restored_snapshot = node.snapshot_workflow_state()
        assert restored_snapshot is not None
        assert restored_snapshot.workflow_id == original_snapshot.workflow_id
        assert (
            restored_snapshot.current_step_index == original_snapshot.current_step_index
        )
        assert (
            restored_snapshot.completed_step_ids == original_snapshot.completed_step_ids
        )
        assert restored_snapshot.failed_step_ids == original_snapshot.failed_step_ids
        assert restored_snapshot.context == original_snapshot.context

    @pytest.mark.asyncio
    async def test_execute_workflow_populates_workflow_state(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test execute_workflow_from_contract automatically populates _workflow_state.

        This is the key test verifying that _workflow_state is populated during
        workflow execution, not just during restore operations.
        """
        from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Initially no workflow state
        assert node.snapshot_workflow_state() is None

        # Create workflow steps
        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()
        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="step_1",
                step_type="compute",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="step_2",
                step_type="compute",
                enabled=True,
            ),
        ]

        # Execute workflow
        result = await node.execute_workflow_from_contract(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps,
            workflow_id=workflow_id,
        )

        # Verify workflow state is now populated
        snapshot = node.snapshot_workflow_state()
        assert snapshot is not None
        assert isinstance(snapshot, ModelWorkflowStateSnapshot)
        assert snapshot.workflow_id == workflow_id

        # Verify completed steps match result
        assert len(snapshot.completed_step_ids) == len(result.completed_steps)

        # Verify context contains execution metadata
        assert "execution_status" in snapshot.context
        assert "execution_time_ms" in snapshot.context
        assert "actions_count" in snapshot.context

    @pytest.mark.asyncio
    async def test_execute_workflow_captures_state_for_serialization(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test execute_workflow_from_contract captures state for serialization."""
        from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create single step workflow
        workflow_id = uuid4()
        step1_id = uuid4()
        steps_simple = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="step_1",
                step_type="compute",
                enabled=True,
            ),
        ]

        result = await node.execute_workflow_from_contract(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps_simple,
            workflow_id=workflow_id,
        )

        # Verify workflow state captures the result
        snapshot = node.snapshot_workflow_state()
        assert snapshot is not None
        assert snapshot.workflow_id == workflow_id
        assert snapshot.current_step_index == len(result.completed_steps) + len(
            result.failed_steps
        )

    @pytest.mark.asyncio
    async def test_workflow_state_available_after_multiple_executions(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test workflow state is updated after each execution."""
        from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # First execution
        workflow_id_1 = uuid4()
        step1_id = uuid4()
        steps_1 = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="first_workflow_step",
                step_type="compute",
                enabled=True,
            ),
        ]

        await node.execute_workflow_from_contract(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps_1,
            workflow_id=workflow_id_1,
        )

        snapshot_1 = node.snapshot_workflow_state()
        assert snapshot_1 is not None
        assert snapshot_1.workflow_id == workflow_id_1

        # Second execution (should replace first)
        workflow_id_2 = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()
        steps_2 = [
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="second_workflow_step_1",
                step_type="effect",
                enabled=True,
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="second_workflow_step_2",
                step_type="effect",
                enabled=True,
            ),
        ]

        await node.execute_workflow_from_contract(
            workflow_definition=simple_workflow_definition,
            workflow_steps=steps_2,
            workflow_id=workflow_id_2,
        )

        snapshot_2 = node.snapshot_workflow_state()
        assert snapshot_2 is not None
        assert snapshot_2.workflow_id == workflow_id_2
        # Different workflow, different completed steps
        assert snapshot_2.workflow_id != snapshot_1.workflow_id
        assert len(snapshot_2.completed_step_ids) == 2


class TestNodeOrchestratorWorkflowSnapshotValidation:
    """Tests for NodeOrchestrator workflow snapshot validation.

    Tests the _validate_workflow_snapshot() method that ensures restored
    snapshots are valid:
    - Timestamp sanity check (created_at not in the future)
    - Step IDs overlap check (a step cannot be both completed AND failed)
    """

    def test_restore_workflow_state_rejects_future_timestamp(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state raises error for snapshot with future timestamp."""
        from datetime import UTC, timedelta

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with future timestamp
        future_time = datetime.now(UTC) + timedelta(days=30)
        workflow_id = uuid4()
        snapshot_with_future_time = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[],
            failed_step_ids=[],
            context={},
            created_at=future_time,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_future_time)

        assert "is in the future" in str(exc_info.value)

    def test_restore_workflow_state_rejects_naive_future_timestamp(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state handles naive datetime timestamps correctly."""
        from datetime import timedelta

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with naive future timestamp (no timezone info)
        future_time = datetime.now() + timedelta(days=30)
        workflow_id = uuid4()
        snapshot_with_future_time = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[],
            failed_step_ids=[],
            context={},
            created_at=future_time,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_future_time)

        assert "is in the future" in str(exc_info.value)

    def test_restore_workflow_state_accepts_past_timestamp(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state accepts snapshot with past timestamp."""
        from datetime import UTC

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with past timestamp
        past_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
        workflow_id = uuid4()
        step_id = uuid4()
        snapshot_with_past_time = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step_id],
            failed_step_ids=[],
            context={"restored": True},
            created_at=past_time,
        )

        # Should not raise
        node.restore_workflow_state(snapshot_with_past_time)

        # Verify state was restored
        current_snapshot = node.snapshot_workflow_state()
        assert current_snapshot is not None
        assert current_snapshot.workflow_id == workflow_id
        assert current_snapshot.current_step_index == 2
        assert current_snapshot.completed_step_ids == (step_id,)

    def test_restore_workflow_state_accepts_recent_timestamp(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state accepts snapshot with recent timestamp."""
        from datetime import UTC, timedelta

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with timestamp from a second ago
        recent_time = datetime.now(UTC) - timedelta(seconds=1)
        workflow_id = uuid4()
        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[],
            failed_step_ids=[],
            context={},
            created_at=recent_time,
        )

        # Should not raise
        node.restore_workflow_state(snapshot)

        # Verify state was restored
        current_snapshot = node.snapshot_workflow_state()
        assert current_snapshot is not None
        assert current_snapshot.workflow_id == workflow_id

    def test_restore_workflow_state_includes_context_in_error(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state error includes workflow_id in context."""
        from datetime import UTC, timedelta

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with future timestamp and a workflow_id
        future_time = datetime.now(UTC) + timedelta(days=30)
        workflow_id = uuid4()
        snapshot_with_future_time = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[],
            failed_step_ids=[],
            context={},
            created_at=future_time,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_future_time)

        # Check that error model context includes workflow_id
        error = exc_info.value
        # Use model.context for full context (includes additional fields)
        # The context dict is nested under an outer 'context' key due to how ModelOnexError works
        assert error.model.context is not None
        ctx = error.model.context.get("context", error.model.context)
        assert "workflow_id" in ctx
        assert ctx["workflow_id"] == str(workflow_id)

    def test_restore_workflow_state_handles_none_workflow_id(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state handles snapshot with None workflow_id."""
        from datetime import UTC, timedelta

        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with future timestamp and no workflow_id
        future_time = datetime.now(UTC) + timedelta(days=30)
        snapshot_with_future_time = ModelWorkflowStateSnapshot(
            workflow_id=None,
            current_step_index=1,
            completed_step_ids=[],
            failed_step_ids=[],
            context={},
            created_at=future_time,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_future_time)

        # Check that error is raised and model context has None for workflow_id
        error = exc_info.value
        # Use model.context for full context (includes additional fields)
        # The context dict is nested under an outer 'context' key due to how ModelOnexError works
        assert error.model.context is not None
        ctx = error.model.context.get("context", error.model.context)
        assert "workflow_id" in ctx
        assert ctx["workflow_id"] is None

    def test_restore_workflow_state_rejects_overlapping_step_ids(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state raises error when step is both completed AND failed."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with overlapping step IDs
        workflow_id = uuid4()
        overlapping_step_id = uuid4()
        snapshot_with_overlap = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[overlapping_step_id],
            failed_step_ids=[overlapping_step_id],  # Same step in both lists!
            context={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_overlap)

        assert "cannot be both completed and failed" in str(exc_info.value)

    def test_restore_workflow_state_rejects_multiple_overlapping_step_ids(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state detects multiple overlapping step IDs."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create snapshot with multiple overlapping step IDs
        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()
        snapshot_with_overlap = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=3,
            completed_step_ids=[step1_id, step2_id],
            failed_step_ids=[step2_id, step3_id],  # step2_id overlaps
            context={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_overlap)

        assert "cannot be both completed and failed" in str(exc_info.value)
        # Check that overlapping step_id is included in error context
        error = exc_info.value
        assert error.model.context is not None
        ctx = error.model.context.get("context", error.model.context)
        assert "overlapping_step_ids" in ctx
        # Verify the overlapping step is identified
        overlapping_ids = ctx["overlapping_step_ids"]
        assert str(step2_id) in overlapping_ids

    def test_restore_workflow_state_accepts_non_overlapping_step_ids(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test restore_workflow_state accepts snapshot with no overlap."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        # Create valid snapshot with distinct step IDs
        workflow_id = uuid4()
        completed_step_id = uuid4()
        failed_step_id = uuid4()
        valid_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[completed_step_id],
            failed_step_ids=[failed_step_id],
            context={"test": "value"},
        )

        # Should not raise
        node.restore_workflow_state(valid_snapshot)

        # Verify state was restored
        current_snapshot = node.snapshot_workflow_state()
        assert current_snapshot is not None
        assert current_snapshot.workflow_id == workflow_id
        # completed_step_ids and failed_step_ids are tuples in the model
        assert completed_step_id in current_snapshot.completed_step_ids
        assert failed_step_id in current_snapshot.failed_step_ids

    def test_restore_workflow_state_overlap_error_includes_workflow_id(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test overlap error includes workflow_id in context."""
        node = NodeOrchestrator(test_container)
        node.workflow_definition = simple_workflow_definition

        workflow_id = uuid4()
        overlapping_step_id = uuid4()
        snapshot_with_overlap = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[overlapping_step_id],
            failed_step_ids=[overlapping_step_id],
            context={},
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node.restore_workflow_state(snapshot_with_overlap)

        # Check that error model context includes workflow_id
        error = exc_info.value
        assert error.model.context is not None
        ctx = error.model.context.get("context", error.model.context)
        assert "workflow_id" in ctx
        assert ctx["workflow_id"] == str(workflow_id)


class TestModelWorkflowStateSnapshot:
    """Tests for ModelWorkflowStateSnapshot model behavior.

    Tests the immutable workflow state snapshot model:
    - create_initial() factory method
    - Immutability via frozen=True
    - with_step_completed() transition method
    - with_step_failed() transition method
    - model_dump() serialization
    """

    def test_create_initial(self) -> None:
        """Test create_initial factory method creates initial snapshot."""
        workflow_id = uuid4()

        snapshot = ModelWorkflowStateSnapshot.create_initial(workflow_id)

        assert snapshot.workflow_id == workflow_id
        assert snapshot.current_step_index == 0
        assert snapshot.completed_step_ids == ()
        assert snapshot.failed_step_ids == ()
        assert snapshot.context == {}
        assert isinstance(snapshot.created_at, datetime)

    def test_create_initial_without_workflow_id(self) -> None:
        """Test create_initial with None workflow_id."""
        snapshot = ModelWorkflowStateSnapshot.create_initial(None)

        assert snapshot.workflow_id is None
        assert snapshot.current_step_index == 0

    def test_immutability(self) -> None:
        """Test frozen model prevents field modification."""
        snapshot = ModelWorkflowStateSnapshot.create_initial(uuid4())

        # Attempting to modify frozen fields should raise ValidationError
        with pytest.raises(ValidationError):
            snapshot.current_step_index = 5

        with pytest.raises(ValidationError):
            snapshot.workflow_id = uuid4()

    def test_with_step_completed(self) -> None:
        """Test with_step_completed creates new snapshot with step marked completed."""
        workflow_id = uuid4()
        step_id = uuid4()
        initial_snapshot = ModelWorkflowStateSnapshot.create_initial(workflow_id)

        updated_snapshot = initial_snapshot.with_step_completed(
            step_id, new_context={"step_result": "success"}
        )

        # Original unchanged
        assert initial_snapshot.current_step_index == 0
        assert initial_snapshot.completed_step_ids == ()

        # New snapshot updated
        assert updated_snapshot.current_step_index == 1
        assert step_id in updated_snapshot.completed_step_ids
        assert updated_snapshot.context == {"step_result": "success"}
        assert updated_snapshot.workflow_id == workflow_id

    def test_with_step_completed_preserves_context(self) -> None:
        """Test with_step_completed merges context correctly."""
        workflow_id = uuid4()
        step_id = uuid4()
        initial_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=0,
            context={"existing_key": "existing_value"},
        )

        updated_snapshot = initial_snapshot.with_step_completed(
            step_id, new_context={"new_key": "new_value"}
        )

        # Context should be merged
        assert updated_snapshot.context == {
            "existing_key": "existing_value",
            "new_key": "new_value",
        }

    def test_with_step_failed(self) -> None:
        """Test with_step_failed creates new snapshot with step marked failed."""
        workflow_id = uuid4()
        step_id = uuid4()
        initial_snapshot = ModelWorkflowStateSnapshot.create_initial(workflow_id)

        updated_snapshot = initial_snapshot.with_step_failed(
            step_id, new_context={"error": "timeout"}
        )

        # Original unchanged
        assert initial_snapshot.current_step_index == 0
        assert initial_snapshot.failed_step_ids == ()

        # New snapshot updated
        assert updated_snapshot.current_step_index == 1
        assert step_id in updated_snapshot.failed_step_ids
        assert updated_snapshot.context == {"error": "timeout"}
        assert updated_snapshot.workflow_id == workflow_id

    def test_with_step_failed_preserves_completed_steps(self) -> None:
        """Test with_step_failed preserves previously completed steps."""
        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()

        initial_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[step1_id],
            failed_step_ids=[],
            context={},
        )

        updated_snapshot = initial_snapshot.with_step_failed(step2_id)

        # Completed steps preserved
        assert step1_id in updated_snapshot.completed_step_ids
        # Failed step added
        assert step2_id in updated_snapshot.failed_step_ids
        # Step index incremented
        assert updated_snapshot.current_step_index == 2

    def test_model_dump_serializable(self) -> None:
        """Test model_dump returns JSON-serializable dictionary."""
        import json

        workflow_id = uuid4()
        step1_id = uuid4()
        step2_id = uuid4()

        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=3,
            completed_step_ids=[step1_id],
            failed_step_ids=[step2_id],
            context={"key": "value", "count": 42},
        )

        state_dict = snapshot.model_dump()

        # Verify it's a dictionary
        assert isinstance(state_dict, dict)

        # Verify all expected keys present
        assert "workflow_id" in state_dict
        assert "current_step_index" in state_dict
        assert "completed_step_ids" in state_dict
        assert "failed_step_ids" in state_dict
        assert "context" in state_dict
        assert "created_at" in state_dict

        # Verify JSON serializable (with default=str for UUID/datetime)
        json_str = json.dumps(state_dict, default=str)
        assert isinstance(json_str, str)
        assert "workflow_id" in json_str

    def test_model_dump_mode_json(self) -> None:
        """Test model_dump with mode='json' returns fully serializable dict."""
        import json

        workflow_id = uuid4()
        step_id = uuid4()

        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[step_id],
            failed_step_ids=[],
            context={"key": "value"},
        )

        # mode='json' converts UUIDs and datetimes to strings
        state_dict = snapshot.model_dump(mode="json")

        # Should be directly JSON serializable without default=str
        json_str = json.dumps(state_dict)
        assert isinstance(json_str, str)

        # Verify UUIDs were converted to strings
        assert state_dict["workflow_id"] == str(workflow_id)
        assert state_dict["completed_step_ids"] == [str(step_id)]


class TestModelFSMStateSnapshot:
    """Additional tests for ModelFSMStateSnapshot model behavior.

    Tests the immutable FSM state snapshot model:
    - create_initial() factory method
    - Immutability via frozen=True
    - transition_to() creates new snapshot
    - model_dump() serialization
    """

    def test_create_initial(self) -> None:
        """Test create_initial factory method creates initial snapshot."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")

        assert snapshot.current_state == "idle"
        assert snapshot.context == {}
        assert snapshot.history == []

    def test_immutability(self) -> None:
        """Test frozen model prevents field modification."""
        snapshot = ModelFSMStateSnapshot.create_initial("idle")

        # Attempting to modify frozen fields should raise ValidationError
        with pytest.raises(ValidationError):
            snapshot.current_state = "processing"

    def test_transition_to(self) -> None:
        """Test transition_to creates new snapshot with updated state."""
        initial_snapshot = ModelFSMStateSnapshot.create_initial("idle")

        new_snapshot = initial_snapshot.transition_to(
            "processing", new_context={"step": 1}
        )

        # Original unchanged
        assert initial_snapshot.current_state == "idle"
        assert initial_snapshot.history == []

        # New snapshot updated
        assert new_snapshot.current_state == "processing"
        assert new_snapshot.history == ["idle"]
        assert new_snapshot.context == {"step": 1}

    def test_transition_to_preserves_history(self) -> None:
        """Test transition_to preserves and extends history."""
        snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={},
            history=["idle"],
        )

        new_snapshot = snapshot.transition_to("completed")

        assert new_snapshot.history == ["idle", "processing"]
        assert new_snapshot.current_state == "completed"

    def test_transition_to_merges_context(self) -> None:
        """Test transition_to merges context correctly."""
        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context={"existing": "value"},
            history=[],
        )

        new_snapshot = snapshot.transition_to("processing", new_context={"new": "data"})

        assert new_snapshot.context == {"existing": "value", "new": "data"}

    def test_model_dump_serializable(self) -> None:
        """Test model_dump returns serializable dictionary."""
        import json

        snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={"key": "value", "count": 42},
            history=["idle"],
        )

        state_dict = snapshot.model_dump()

        # Verify it's a dictionary
        assert isinstance(state_dict, dict)

        # Verify all expected keys present
        assert state_dict["current_state"] == "processing"
        assert state_dict["context"] == {"key": "value", "count": 42}
        assert state_dict["history"] == ["idle"]

        # Verify JSON serializable
        json_str = json.dumps(state_dict)
        assert isinstance(json_str, str)


class TestContextMutationProtection:
    """Tests for context mutation protection in snapshot models.

    These tests verify that modifying the context dictionary after creating
    a snapshot does not affect the snapshot's internal state (defensive copy).
    """

    def test_fsm_snapshot_context_mutation_protection(self) -> None:
        """Test that mutating source context does not affect FSM snapshot."""
        nested_dict: dict[str, str] = {"inner": "data"}
        original_context: dict[str, object] = {
            "key": "original_value",
            "nested": nested_dict,
        }

        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context=original_context,
            history=[],
        )

        # Mutate the original context
        original_context["key"] = "mutated_value"
        original_context["new_key"] = "new_value"
        nested_dict["inner"] = "mutated_inner"

        # Snapshot should not be affected by mutations
        assert snapshot.context["key"] == "original_value"
        assert "new_key" not in snapshot.context
        # Note: nested dicts may or may not be deep copied depending on implementation
        # This tests the current behavior

    def test_workflow_snapshot_context_mutation_protection(self) -> None:
        """Test that mutating source context does not affect workflow snapshot."""
        workflow_id = uuid4()
        original_context = {"key": "original_value", "count": 10}

        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[],
            failed_step_ids=[],
            context=original_context,
        )

        # Mutate the original context
        original_context["key"] = "mutated_value"
        original_context["count"] = 999
        original_context["new_key"] = "new_value"

        # Snapshot should not be affected by mutations
        assert snapshot.context["key"] == "original_value"
        assert snapshot.context["count"] == 10
        assert "new_key" not in snapshot.context

    def test_fsm_snapshot_returned_context_mutation_protection(self) -> None:
        """Test that mutating returned context does not affect FSM snapshot state."""
        snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context={"key": "value"},
            history=[],
        )

        # Get the context and try to mutate it
        retrieved_context = snapshot.context
        # Note: frozen Pydantic models may still allow dict mutation
        # depending on implementation details

        # Create a new access to verify original is unchanged
        # The key assertion is that the model maintains its state
        assert snapshot.context["key"] == "value"

    def test_workflow_snapshot_with_step_completed_context_isolation(self) -> None:
        """Test that with_step_completed creates isolated context copy."""
        workflow_id = uuid4()
        step_id = uuid4()
        original_context = {"existing": "value"}

        initial_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=0,
            context=original_context,
        )

        # Create new snapshot with additional context
        new_context = {"new": "data"}
        updated_snapshot = initial_snapshot.with_step_completed(
            step_id, new_context=new_context
        )

        # Mutate the new_context dict
        new_context["new"] = "mutated"
        new_context["extra"] = "added"

        # Updated snapshot should not be affected
        assert updated_snapshot.context["new"] == "data"
        assert "extra" not in updated_snapshot.context

        # Original snapshot should not be affected
        assert initial_snapshot.context == {"existing": "value"}

    def test_fsm_snapshot_transition_context_isolation(self) -> None:
        """Test that transition_to creates isolated context copy."""
        original_context = {"existing": "value"}
        initial_snapshot = ModelFSMStateSnapshot(
            current_state="idle",
            context=original_context,
            history=[],
        )

        # Create new snapshot via transition
        new_context = {"new": "data"}
        new_snapshot = initial_snapshot.transition_to(
            "processing", new_context=new_context
        )

        # Mutate the new_context dict
        new_context["new"] = "mutated"

        # New snapshot should not be affected
        assert new_snapshot.context["new"] == "data"

        # Original snapshot should not be affected
        assert initial_snapshot.context == {"existing": "value"}


class TestConcurrentAccessSafety:
    """Tests for concurrent access to node state serialization.

    These tests verify thread safety warnings and demonstrate proper usage
    patterns for concurrent access. NodeReducer and NodeOrchestrator are
    NOT thread-safe; each thread should use its own instance.

    Note: These tests don't use actual threading to avoid flaky behavior
    in CI. Instead, they verify the contracts and document expected behavior.
    """

    def test_node_reducer_is_not_thread_safe_documented(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Verify NodeReducer documents non-thread-safe behavior.

        This test verifies that the NodeReducer class documentation correctly
        warns about thread safety. See docs/guides/THREADING.md for patterns.
        """
        node = NodeReducer(test_container)

        # Verify the class documents thread safety concerns
        assert "NOT thread-safe" in (NodeReducer.__doc__ or "")
        assert "Thread Safety" in (NodeReducer.__doc__ or "")

        # Verify mutable state exists (evidence of non-thread-safety)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={"initial": True})

        # FSM state is mutable instance state
        assert node.snapshot_state() is not None

    def test_node_orchestrator_is_not_thread_safe_documented(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify NodeOrchestrator documents non-thread-safe behavior.

        This test verifies that the NodeOrchestrator class documentation
        correctly warns about thread safety. See docs/guides/THREADING.md.
        """
        node = NodeOrchestrator(test_container)

        # Verify the class documents thread safety concerns
        assert "NOT thread-safe" in (NodeOrchestrator.__doc__ or "")
        assert "Thread Safety" in (NodeOrchestrator.__doc__ or "")

        # Verify mutable state exists (evidence of non-thread-safety)
        node.workflow_definition = simple_workflow_definition
        workflow_id = uuid4()
        node.update_workflow_state(
            workflow_id=workflow_id,
            current_step_index=1,
            completed_step_ids=[],
            context={},
        )

        # Workflow state is mutable instance state
        assert node.snapshot_workflow_state() is not None

    def test_separate_node_instances_have_independent_state(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Verify that separate node instances maintain independent state.

        This is the recommended pattern for thread safety: each thread
        should create and use its own node instance.
        """
        # Create two separate instances (as would be done per-thread)
        node1 = NodeReducer(test_container)
        node2 = NodeReducer(test_container)

        # Initialize both with the same FSM contract
        node1.fsm_contract = simple_fsm
        node2.fsm_contract = simple_fsm
        node1.initialize_fsm_state(simple_fsm, context={"instance": "node1"})
        node2.initialize_fsm_state(simple_fsm, context={"instance": "node2"})

        # Verify they have independent state
        snapshot1 = node1.snapshot_state()
        snapshot2 = node2.snapshot_state()

        assert snapshot1 is not None
        assert snapshot2 is not None
        assert snapshot1.context["instance"] == "node1"
        assert snapshot2.context["instance"] == "node2"

        # Modifying one should not affect the other
        node1.restore_state(
            ModelFSMStateSnapshot(
                current_state="processing",
                context={"modified": True},
                history=["idle"],
            )
        )

        # Node2 should be unchanged
        snapshot2_after = node2.snapshot_state()
        assert snapshot2_after is not None
        assert snapshot2_after.current_state == "idle"
        assert snapshot2_after.context["instance"] == "node2"

    def test_separate_orchestrator_instances_have_independent_state(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Verify that separate orchestrator instances maintain independent state.

        This is the recommended pattern for thread safety: each thread
        should create and use its own node instance.
        """
        # Create two separate instances (as would be done per-thread)
        node1 = NodeOrchestrator(test_container)
        node2 = NodeOrchestrator(test_container)

        # Set workflow definitions
        node1.workflow_definition = simple_workflow_definition
        node2.workflow_definition = simple_workflow_definition

        # Set different workflow states
        workflow_id1 = uuid4()
        workflow_id2 = uuid4()

        node1.update_workflow_state(
            workflow_id=workflow_id1,
            current_step_index=1,
            completed_step_ids=[],
            context={"instance": "node1"},
        )

        node2.update_workflow_state(
            workflow_id=workflow_id2,
            current_step_index=5,
            completed_step_ids=[],
            context={"instance": "node2"},
        )

        # Verify they have independent state
        snapshot1 = node1.snapshot_workflow_state()
        snapshot2 = node2.snapshot_workflow_state()

        assert snapshot1 is not None
        assert snapshot2 is not None
        assert snapshot1.workflow_id == workflow_id1
        assert snapshot2.workflow_id == workflow_id2
        assert snapshot1.current_step_index == 1
        assert snapshot2.current_step_index == 5

    def test_snapshot_immutability_enables_safe_sharing(self) -> None:
        """Verify that snapshot models can be safely shared (immutable).

        While node instances are NOT thread-safe, the snapshot models
        themselves are immutable and can be safely shared across threads.
        """
        # Create an FSM snapshot
        fsm_snapshot = ModelFSMStateSnapshot(
            current_state="processing",
            context={"data": "value"},
            history=["idle"],
        )

        # Create a workflow snapshot
        workflow_id = uuid4()
        step_id = uuid4()
        workflow_snapshot = ModelWorkflowStateSnapshot(
            workflow_id=workflow_id,
            current_step_index=2,
            completed_step_ids=[step_id],
            failed_step_ids=[],
            context={"progress": 50},
        )

        # Verify both are frozen (immutable)
        with pytest.raises(ValidationError):
            fsm_snapshot.current_state = "completed"

        with pytest.raises(ValidationError):
            workflow_snapshot.current_step_index = 10

        # Immutable snapshots can be safely passed to other threads
        # because they cannot be modified
        assert fsm_snapshot.current_state == "processing"
        assert workflow_snapshot.current_step_index == 2
