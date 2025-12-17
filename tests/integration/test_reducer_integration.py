"""
Integration tests for NodeReducer ModelReducerInput -> ModelReducerOutput flows.

These tests verify complete FSM-driven reducer workflows including:
1. Happy path state transitions
2. Error handling for invalid transitions
3. Multi-step workflow transitions
4. Event-driven workflow with intent emission
5. Recovery workflows with retry patterns

Tests validate real FSM state transitions with actual data, not mocks.

Note:
    Integration tests using these fixtures should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
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
from omnibase_core.models.fsm.model_fsm_state_snapshot import ModelFSMStateSnapshot
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.nodes.node_reducer import NodeReducer

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60

# Version for test contracts
V1_0_0 = ModelSemVer(major=1, minor=0, patch=0)


# Type alias for reducer factory callable
ReducerWithContractFactory = Callable[[ModelFSMSubcontract], NodeReducer[Any, Any]]


def create_test_fsm_contract(
    *,
    name: str = "test_fsm",
    initial_state: str = "idle",
    states: list[dict[str, Any]] | None = None,
    transitions: list[dict[str, Any]] | None = None,
    terminal_states: list[str] | None = None,
    error_states: list[str] | None = None,
) -> ModelFSMSubcontract:
    """Factory to create FSM contracts for testing.

    Args:
        name: State machine name
        initial_state: Initial state name
        states: List of state definition dicts
        transitions: List of transition definition dicts
        terminal_states: List of terminal state names
        error_states: List of error state names

    Returns:
        ModelFSMSubcontract configured for testing
    """
    if states is None:
        states = [
            {
                "version": V1_0_0,
                "state_name": "idle",
                "state_type": "operational",
                "description": "Initial idle state",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "processing",
                "state_type": "operational",
                "description": "Processing data",
                "is_terminal": False,
                "is_recoverable": True,
                "entry_actions": ["log_entry"],
            },
            {
                "version": V1_0_0,
                "state_name": "completed",
                "state_type": "terminal",
                "description": "Processing completed",
                "is_terminal": True,
                "is_recoverable": False,
            },
        ]

    if transitions is None:
        transitions = [
            {
                "version": V1_0_0,
                "transition_name": "start_processing",
                "from_state": "idle",
                "to_state": "processing",
                "trigger": "start",
            },
            {
                "version": V1_0_0,
                "transition_name": "complete_processing",
                "from_state": "processing",
                "to_state": "completed",
                "trigger": "complete",
            },
        ]

    return ModelFSMSubcontract(
        version=V1_0_0,
        state_machine_name=name,
        state_machine_version=V1_0_0,
        description=f"Test FSM: {name}",
        states=[ModelFSMStateDefinition(**s) for s in states],
        initial_state=initial_state,
        transitions=[ModelFSMStateTransition(**t) for t in transitions],
        terminal_states=terminal_states or [],
        error_states=error_states or [],
    )


class TestableNodeReducer(NodeReducer[Any, Any]):
    """Test implementation of NodeReducer that can accept an FSM contract.

    This class exists solely for integration testing purposes. It allows tests
    to inject arbitrary FSM contracts at runtime rather than relying on the
    production contract loading mechanism (which requires class-level attributes
    and YAML contract files).

    WARNING: This pattern is for TESTING ONLY. Production code should always
    use the standard NodeReducer initialization which loads contracts from
    declarative YAML files via class attributes.
    """

    def __init__(
        self, container: ModelONEXContainer, fsm_contract: ModelFSMSubcontract
    ) -> None:
        """Initialize with explicit FSM contract injection.

        This constructor intentionally bypasses the standard NodeReducer.__init__()
        to enable direct FSM contract injection for testing. This is necessary
        because the production NodeReducer expects contracts to be loaded from
        class-level attributes and YAML files, which is not suitable for
        integration tests that need to create dynamic FSM configurations.

        Args:
            container: ONEX container for dependency injection
            fsm_contract: FSM subcontract to use for state machine

        Note:
            The inheritance chain is:
            TestableNodeReducer -> NodeReducer -> NodeCoreBase

            By calling `super(NodeReducer, self).__init__(container)`, we skip
            NodeReducer.__init__() entirely and call NodeCoreBase.__init__()
            directly. This:
            1. Avoids the production contract loading logic in NodeReducer
            2. Still initializes all base class infrastructure from NodeCoreBase
            3. Allows us to manually set fsm_contract and initialize FSM state

            WHY THIS IS SAFE FOR TESTING:
            - NodeCoreBase.__init__() handles container setup and core infrastructure
            - We manually provide the fsm_contract that NodeReducer would load
            - We call initialize_fsm_state() which NodeReducer would also call
            - All FSM functionality works identically to production

            WHY THIS IS NOT FOR PRODUCTION:
            - Production nodes should use declarative YAML contracts
            - Bypassing NodeReducer.__init__() skips validation and logging
            - This pattern makes the contract source non-deterministic
            - Contract loading should be centralized, not scattered
        """
        # SUPER() BYPASS EXPLANATION:
        # --------------------------
        # Normal call: super().__init__(container) -> calls NodeReducer.__init__()
        # Our call: super(NodeReducer, self).__init__(container) -> calls NodeCoreBase.__init__()
        #
        # We use the two-argument form of super() to explicitly skip one level
        # in the inheritance hierarchy. This is a deliberate MRO (Method Resolution
        # Order) manipulation that:
        # - Starts resolution from NodeReducer's parent (NodeCoreBase)
        # - Binds 'self' as the instance
        # - Results in calling NodeCoreBase.__init__(container)
        #
        # This is a TEST PATTERN ONLY - never use in production code.
        super(NodeReducer, self).__init__(container)  # Call NodeCoreBase.__init__

        # Directly inject the FSM contract that would normally be loaded from
        # a YAML file via class attributes in production NodeReducer.
        self.fsm_contract = fsm_contract

        # Initialize FSM state using the injected contract.
        # This is the same call that NodeReducer.__init__() would make,
        # but we're making it ourselves after injecting our test contract.
        self.initialize_fsm_state(fsm_contract, context={})


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing.

    Returns:
        ModelONEXContainer with mocked services.
    """
    container = MagicMock(spec=ModelONEXContainer)
    container.get_service = MagicMock(return_value=MagicMock())
    return container


@pytest.fixture
def reducer_with_contract_factory(
    mock_container: ModelONEXContainer,
) -> ReducerWithContractFactory:
    """Factory fixture for creating NodeReducer instances with custom FSM contracts.

    Args:
        mock_container: Mocked ONEX container

    Returns:
        Factory callable that creates TestableNodeReducer instances
    """

    def _create_reducer(fsm_contract: ModelFSMSubcontract) -> NodeReducer[Any, Any]:
        return TestableNodeReducer(mock_container, fsm_contract)

    return _create_reducer


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestReducerIntegration:
    """Integration tests for NodeReducer input -> output flows.

    Tests complete FSM-driven reducer workflows with real state transitions.
    """

    def test_happy_path_input_to_valid_output(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test Scenario 1: Happy path from ModelReducerInput to ModelReducerOutput.

        This test verifies:
        - Valid ModelReducerInput is created with FSM trigger
        - NodeReducer processes the input through FSM transition
        - ModelReducerOutput contains correct new state
        - FSM state history is properly tracked
        - Intents are emitted for side effects
        """
        # Arrange: Create FSM contract with simple workflow
        fsm_contract = create_test_fsm_contract(
            name="happy_path_fsm",
            initial_state="idle",
        )

        reducer = reducer_with_contract_factory(fsm_contract)

        # Verify initial state
        assert reducer.get_current_state() == "idle"
        assert reducer.get_state_history() == []

        # Create input with trigger to transition from idle -> processing
        input_data: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"key": "value1"}, {"key": "value2"}],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata=ModelReducerMetadata(
                trigger="start",
                source="integration_test",
                correlation_id=str(uuid4()),
            ),
        )

        # Act: Process the input
        result: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input_data)
        )

        # Assert: Verify output structure and state transition
        assert isinstance(result, ModelReducerOutput)
        assert result.operation_id == input_data.operation_id
        assert result.reduction_type == EnumReductionType.AGGREGATE
        assert result.processing_time_ms >= 0.0

        # Verify FSM state transitioned
        assert reducer.get_current_state() == "processing"
        assert reducer.get_state_history() == ["idle"]

        # Verify output metadata contains FSM state info
        assert result.metadata.model_extra.get("fsm_state") == "processing"
        assert result.metadata.model_extra.get("fsm_success") is True

        # Verify intents were emitted (for persistence, metrics, etc.)
        assert len(result.intents) > 0

    def test_error_path_invalid_transition(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test Scenario 2: Error path for invalid FSM transition.

        This test verifies:
        - Invalid trigger that doesn't match any transition
        - NodeReducer raises ModelOnexError
        - FSM state remains unchanged
        - Error contains meaningful context
        """
        # Arrange: Create FSM contract
        fsm_contract = create_test_fsm_contract(
            name="error_path_fsm",
            initial_state="idle",
        )

        reducer = reducer_with_contract_factory(fsm_contract)
        initial_state = reducer.get_current_state()

        # Create input with invalid trigger (no transition from idle with "invalid_trigger")
        input_data: ModelReducerInput[str] = ModelReducerInput(
            data=["item1", "item2"],
            reduction_type=EnumReductionType.FOLD,
            metadata=ModelReducerMetadata(
                trigger="invalid_trigger",
                source="error_test",
            ),
        )

        # Act & Assert: Expect ModelOnexError for invalid transition
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(reducer.process(input_data))

        # Verify error details using specific error code
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

        # Verify FSM state unchanged
        assert reducer.get_current_state() == initial_state
        assert reducer.get_state_history() == []

    def test_multi_step_workflow_transitions(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test Scenario 3: Multi-step workflow with sequential transitions.

        This test verifies:
        - Multiple sequential FSM transitions
        - State history accumulates correctly
        - Each transition produces valid output
        - Final state is correctly reached
        """
        # Arrange: Create FSM contract with 4-state workflow
        states = [
            {
                "version": V1_0_0,
                "state_name": "draft",
                "state_type": "operational",
                "description": "Initial draft state",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "review",
                "state_type": "operational",
                "description": "Under review",
                "is_terminal": False,
                "is_recoverable": True,
                "entry_actions": ["notify_reviewers"],
            },
            {
                "version": V1_0_0,
                "state_name": "approved",
                "state_type": "operational",
                "description": "Approved for deployment",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "deployed",
                "state_type": "terminal",
                "description": "Successfully deployed",
                "is_terminal": True,
                "is_recoverable": False,
            },
        ]

        transitions = [
            {
                "version": V1_0_0,
                "transition_name": "submit_for_review",
                "from_state": "draft",
                "to_state": "review",
                "trigger": "submit",
            },
            {
                "version": V1_0_0,
                "transition_name": "approve_review",
                "from_state": "review",
                "to_state": "approved",
                "trigger": "approve",
            },
            {
                "version": V1_0_0,
                "transition_name": "deploy_change",
                "from_state": "approved",
                "to_state": "deployed",
                "trigger": "deploy",
            },
        ]

        fsm_contract = create_test_fsm_contract(
            name="multi_step_workflow",
            initial_state="draft",
            states=states,
            transitions=transitions,
            terminal_states=["deployed"],
        )

        reducer = reducer_with_contract_factory(fsm_contract)

        # Step 1: draft -> review
        input1: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"change_id": "CHG-001"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="submit"),
        )
        result1: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input1)
        )

        assert result1.metadata.model_extra.get("fsm_state") == "review"
        assert reducer.get_current_state() == "review"
        assert reducer.get_state_history() == ["draft"]

        # Step 2: review -> approved
        input2: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"approver": "reviewer@test.com"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="approve"),
        )
        result2: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input2)
        )

        assert result2.metadata.model_extra.get("fsm_state") == "approved"
        assert reducer.get_current_state() == "approved"
        assert reducer.get_state_history() == ["draft", "review"]

        # Step 3: approved -> deployed
        input3: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"deployment_id": "DEP-001"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="deploy"),
        )
        result3: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input3)
        )

        assert result3.metadata.model_extra.get("fsm_state") == "deployed"
        assert reducer.get_current_state() == "deployed"
        assert reducer.get_state_history() == ["draft", "review", "approved"]

        # Verify terminal state
        assert reducer.is_complete() is True

    def test_event_driven_workflow(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test Scenario 4: Event-driven workflow with intent emission.

        This test verifies:
        - FSM transitions emit intents for side effects
        - Entry/exit actions generate appropriate intents
        - Persistence intents are created when enabled
        - Metrics intents are created for monitoring
        """
        # Arrange: Create FSM with entry/exit actions
        states = [
            {
                "version": V1_0_0,
                "state_name": "waiting",
                "state_type": "operational",
                "description": "Waiting for events",
                "is_terminal": False,
                "is_recoverable": True,
                "exit_actions": ["log_exit_waiting"],
            },
            {
                "version": V1_0_0,
                "state_name": "processing_event",
                "state_type": "operational",
                "description": "Processing incoming event",
                "is_terminal": False,
                "is_recoverable": True,
                "entry_actions": ["start_event_processing", "emit_event_received"],
                "exit_actions": ["cleanup_event"],
            },
            {
                "version": V1_0_0,
                "state_name": "event_handled",
                "state_type": "terminal",
                "description": "Event successfully handled",
                "is_terminal": True,
                "is_recoverable": False,
            },
        ]

        transitions = [
            {
                "version": V1_0_0,
                "transition_name": "receive_event",
                "from_state": "waiting",
                "to_state": "processing_event",
                "trigger": "event_received",
            },
            {
                "version": V1_0_0,
                "transition_name": "finish_processing",
                "from_state": "processing_event",
                "to_state": "event_handled",
                "trigger": "event_processed",
            },
        ]

        fsm_contract = create_test_fsm_contract(
            name="event_driven_fsm",
            initial_state="waiting",
            states=states,
            transitions=transitions,
            terminal_states=["event_handled"],
        )

        reducer = reducer_with_contract_factory(fsm_contract)

        # Trigger event-driven transition
        input_data: ModelReducerInput[dict[str, Any]] = ModelReducerInput(
            data=[{"event_type": "user_action", "payload": {"action": "click"}}],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata=ModelReducerMetadata(
                trigger="event_received",
                source="event_bus",
                correlation_id=str(uuid4()),
            ),
        )

        result: ModelReducerOutput[dict[str, Any]] = asyncio.run(
            reducer.process(input_data)
        )

        # Verify state transition
        assert reducer.get_current_state() == "processing_event"

        # Verify intents were emitted
        assert len(result.intents) > 0

        # Check for specific intent types
        intent_types = {intent.intent_type for intent in result.intents}

        # Should have:
        # - fsm_state_action for exit actions (log_exit_waiting)
        # - fsm_state_action for entry actions (start_event_processing, emit_event_received)
        # - persist_state for state persistence
        # - record_metric for monitoring
        # NOTE: These intent types are part of the stable FSM contract API.
        # See omnibase_core/models/fsm/ for the canonical intent type definitions.
        assert "fsm_state_action" in intent_types
        assert "persist_state" in intent_types
        assert "record_metric" in intent_types

        # Verify intent payloads contain correct FSM info
        persist_intents = [
            i for i in result.intents if i.intent_type == "persist_state"
        ]
        assert len(persist_intents) == 1
        assert persist_intents[0].payload["fsm_name"] == "event_driven_fsm"
        assert persist_intents[0].payload["state"] == "processing_event"

    def test_recovery_workflow_retry_success(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test Scenario 5: Recovery workflow with state restoration.

        This test verifies:
        - State can be saved via snapshot before risky operation
        - State can be restored after failure
        - Recovery allows retry of the operation
        - Final success after recovery
        """
        # Arrange: Create FSM with conditional transitions
        states = [
            {
                "version": V1_0_0,
                "state_name": "ready",
                "state_type": "operational",
                "description": "Ready to process",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "validating",
                "state_type": "operational",
                "description": "Validating input",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "executing",
                "state_type": "operational",
                "description": "Executing operation",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "success",
                "state_type": "terminal",
                "description": "Operation succeeded",
                "is_terminal": True,
                "is_recoverable": False,
            },
        ]

        transitions = [
            {
                "version": V1_0_0,
                "transition_name": "start_validation",
                "from_state": "ready",
                "to_state": "validating",
                "trigger": "validate",
            },
            {
                "version": V1_0_0,
                "transition_name": "begin_execution",
                "from_state": "validating",
                "to_state": "executing",
                "trigger": "execute",
                "conditions": [
                    ModelFSMTransitionCondition(
                        condition_name="validation_passed",
                        condition_type="expression",
                        expression="validation_status == passed",
                        required=True,
                    ),
                ],
            },
            {
                "version": V1_0_0,
                "transition_name": "complete_success",
                "from_state": "executing",
                "to_state": "success",
                "trigger": "complete",
            },
        ]

        fsm_contract = create_test_fsm_contract(
            name="recovery_workflow",
            initial_state="ready",
            states=states,
            transitions=transitions,
            terminal_states=["success"],
        )

        reducer = reducer_with_contract_factory(fsm_contract)

        # Step 1: Transition to validating state
        input1: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"item": "data"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="validate"),
        )
        asyncio.run(reducer.process(input1))
        assert reducer.get_current_state() == "validating"

        # Save state snapshot before attempting risky transition
        saved_snapshot = reducer.snapshot_state(deep_copy=True)
        assert saved_snapshot is not None
        assert saved_snapshot.current_state == "validating"

        # Step 2: Attempt transition with failing condition (validation_status != passed)
        # Note: Conditions are evaluated against the context dict which includes
        # metadata fields. We use ModelReducerMetadata's extra="allow" to pass
        # the validation_status at the root context level where conditions can access it.
        #
        # WHY model_construct() IS USED HERE:
        # -----------------------------------
        # model_construct() bypasses Pydantic validation to inject arbitrary extra
        # fields (validation_status) that are not defined in ModelReducerMetadata's
        # schema. This is a TEST PATTERN ONLY that allows us to test FSM condition
        # evaluation without defining custom metadata models for each test case.
        #
        # In production, use properly typed models with explicit field definitions.
        # Bypassing validation can mask type errors and schema violations.
        input2_fail: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"item": "data"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata.model_construct(
                trigger="execute",
                validation_status="failed",  # Extra field for condition evaluation
            ),
        )

        # This should not raise but return failure result (conditions not met)
        result_fail: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input2_fail)
        )

        # Transition fails - state stays at validating but we get a failure result
        assert result_fail.metadata.model_extra.get("fsm_success") is False
        assert reducer.get_current_state() == "validating"

        # Step 3: Restore to saved state (simulating recovery after examining failure)
        reducer.restore_state(saved_snapshot)
        assert reducer.get_current_state() == "validating"

        # Step 4: Retry with correct data (validation_status == passed)
        # Pass validation_status="passed" in metadata extra fields.
        # See comment in Step 2 above for why model_construct() is used here.
        input2_success: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"item": "data"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata.model_construct(
                trigger="execute",
                validation_status="passed",  # Extra field for condition evaluation
            ),
        )

        result_success: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input2_success)
        )

        # Verify successful transition
        assert result_success.metadata.model_extra.get("fsm_success") is True
        assert reducer.get_current_state() == "executing"

        # Step 5: Complete the workflow
        input3: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"result": "done"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="complete"),
        )
        result_final: ModelReducerOutput[dict[str, str]] = asyncio.run(
            reducer.process(input3)
        )

        assert result_final.metadata.model_extra.get("fsm_state") == "success"
        assert reducer.get_current_state() == "success"
        assert reducer.is_complete() is True


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestReducerIntegrationEdgeCases:
    """Additional integration tests for edge cases and boundary conditions.

    Tests verify:
    1. Streaming mode batch processing with large datasets
    2. Conflict resolution metadata preservation
    3. Windowed streaming with window metadata
    4. Terminal state enforcement (no further transitions)
    5. Snapshot/restore context preservation

    Note: 60-second timeout protects against execution hangs.
    """

    def test_streaming_mode_batch_processing(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test reducer with batch streaming mode and large data."""
        fsm_contract = create_test_fsm_contract(name="batch_test")
        reducer = reducer_with_contract_factory(fsm_contract)

        # Create input with large batch
        large_data = [{"id": i, "value": f"item_{i}"} for i in range(100)]

        input_data: ModelReducerInput[dict[str, Any]] = ModelReducerInput(
            data=large_data,
            reduction_type=EnumReductionType.AGGREGATE,
            streaming_mode=EnumStreamingMode.BATCH,
            batch_size=1000,
            metadata=ModelReducerMetadata(trigger="start"),
        )

        result: ModelReducerOutput[dict[str, Any]] = asyncio.run(
            reducer.process(input_data)
        )

        assert result.items_processed == 100
        assert result.streaming_mode == EnumStreamingMode.BATCH
        assert result.batches_processed == 1

    def test_conflict_resolution_metadata_preservation(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test that conflict resolution settings are preserved in output."""
        fsm_contract = create_test_fsm_contract(name="conflict_test")
        reducer = reducer_with_contract_factory(fsm_contract)

        input_data: ModelReducerInput[str] = ModelReducerInput(
            data=["a", "b", "c"],
            reduction_type=EnumReductionType.MERGE,
            conflict_resolution=EnumConflictResolution.MERGE,
            metadata=ModelReducerMetadata(
                trigger="start",
                tags=["test", "integration"],
                partition_id=uuid4(),
            ),
        )

        result: ModelReducerOutput[str] = asyncio.run(reducer.process(input_data))

        # Verify metadata is preserved
        assert result.metadata.tags == ["test", "integration"]
        assert result.metadata.partition_id is not None

    def test_windowed_streaming_metadata(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test windowed streaming mode with window metadata."""
        fsm_contract = create_test_fsm_contract(name="windowed_test")
        reducer = reducer_with_contract_factory(fsm_contract)

        window_id = uuid4()
        input_data: ModelReducerInput[int] = ModelReducerInput(
            data=[1, 2, 3, 4, 5],
            reduction_type=EnumReductionType.FOLD,
            streaming_mode=EnumStreamingMode.WINDOWED,
            window_size_ms=5000,
            metadata=ModelReducerMetadata(
                trigger="start",
                window_id=window_id,
            ),
        )

        result: ModelReducerOutput[int] = asyncio.run(reducer.process(input_data))

        assert result.streaming_mode == EnumStreamingMode.WINDOWED
        assert result.metadata.window_id == window_id

    def test_terminal_state_no_further_transitions(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test that no transitions are possible from terminal state."""
        fsm_contract = create_test_fsm_contract(
            name="terminal_test",
            terminal_states=["completed"],
        )
        reducer = reducer_with_contract_factory(fsm_contract)

        # Transition to processing
        input1: ModelReducerInput[str] = ModelReducerInput(
            data=["data"],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="start"),
        )
        asyncio.run(reducer.process(input1))

        # Transition to completed (terminal)
        input2: ModelReducerInput[str] = ModelReducerInput(
            data=["data"],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="complete"),
        )
        asyncio.run(reducer.process(input2))

        assert reducer.get_current_state() == "completed"
        assert reducer.is_complete() is True

        # Attempt further transition should fail
        input3: ModelReducerInput[str] = ModelReducerInput(
            data=["data"],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(trigger="any_trigger"),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(reducer.process(input3))

        # Verify error code for invalid transition from terminal state
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_snapshot_and_restore_preserves_context(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test that snapshot/restore preserves full FSM context."""
        fsm_contract = create_test_fsm_contract(name="snapshot_context_test")
        reducer = reducer_with_contract_factory(fsm_contract)

        # Transition to processing
        input1: ModelReducerInput[dict[str, Any]] = ModelReducerInput(
            data=[{"key": "value"}],
            reduction_type=EnumReductionType.TRANSFORM,
            metadata=ModelReducerMetadata(
                trigger="start",
                correlation_id="test-correlation-123",
            ),
        )
        asyncio.run(reducer.process(input1))

        # Take snapshot
        snapshot = reducer.snapshot_state(deep_copy=True)
        assert snapshot is not None

        # Verify snapshot structure
        assert snapshot.current_state == "processing"
        assert "idle" in snapshot.history

        # Get dict representation
        snapshot_dict = reducer.get_state_snapshot(deep_copy=True)
        assert snapshot_dict is not None
        assert snapshot_dict["current_state"] == "processing"

        # Create new reducer and restore state
        reducer2 = reducer_with_contract_factory(fsm_contract)
        assert reducer2.get_current_state() == "idle"  # Fresh start

        reducer2.restore_state(snapshot)
        assert reducer2.get_current_state() == "processing"
        assert reducer2.get_state_history() == snapshot.history
