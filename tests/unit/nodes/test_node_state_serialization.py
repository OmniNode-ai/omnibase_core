#!/usr/bin/env python3
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
from omnibase_core.models.fsm.model_fsm_state_snapshot import ModelFSMStateSnapshot
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.workflow.execution.model_workflow_state_snapshot import (
    ModelWorkflowStateSnapshot,
)
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


@pytest.mark.timeout(60)
class TestNodeReducerStateSerialization:
    """Tests for NodeReducer state serialization methods.

    Tests the FSM state snapshot and restoration capabilities:
    - snapshot_state() returns current FSM state
    - restore_state() restores FSM state from snapshot
    - get_state_snapshot() returns dict representation
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
        """Test get_state_snapshot returns dictionary representation."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={"key": "value"})

        state_dict = node.get_state_snapshot()

        assert isinstance(state_dict, dict)
        assert state_dict["current_state"] == "idle"
        assert state_dict["context"] == {"key": "value"}
        assert state_dict["history"] == []

    def test_get_state_snapshot_returns_empty_dict_when_not_initialized(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test get_state_snapshot returns empty dict when FSM not initialized."""
        node = NodeReducer(test_container)

        state_dict = node.get_state_snapshot()

        assert state_dict == {}

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


@pytest.mark.timeout(60)
class TestNodeOrchestratorStateSerialization:
    """Tests for NodeOrchestrator workflow state serialization methods.

    Tests the workflow state snapshot and restoration capabilities:
    - snapshot_workflow_state() returns current workflow state
    - restore_workflow_state() restores workflow state from snapshot
    - get_workflow_snapshot() returns dict representation
    - Round-trip serialization maintains state integrity
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
        assert snapshot.completed_step_ids == [step1_id]
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
        assert current_snapshot.completed_step_ids == [step1_id, step2_id]
        assert current_snapshot.context == {"restored": True, "retry_count": 2}

    def test_get_workflow_snapshot_returns_dict(
        self,
        test_container: ModelONEXContainer,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test get_workflow_snapshot returns dictionary representation."""
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

        state_dict = node.get_workflow_snapshot()

        assert isinstance(state_dict, dict)
        assert state_dict["workflow_id"] == workflow_id
        assert state_dict["current_step_index"] == 2
        assert state_dict["completed_step_ids"] == [step_id]
        assert state_dict["context"] == {"key": "value"}
        assert "created_at" in state_dict

    def test_get_workflow_snapshot_returns_empty_dict_when_not_initialized(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test get_workflow_snapshot returns empty dict when no workflow state."""
        node = NodeOrchestrator(test_container)

        state_dict = node.get_workflow_snapshot()

        assert state_dict == {}

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


@pytest.mark.timeout(60)
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
        assert snapshot.completed_step_ids == []
        assert snapshot.failed_step_ids == []
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
        assert initial_snapshot.completed_step_ids == []

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
        assert initial_snapshot.failed_step_ids == []

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


@pytest.mark.timeout(60)
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
