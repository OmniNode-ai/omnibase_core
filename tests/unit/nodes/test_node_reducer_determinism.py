"""
Unit tests for NodeReducer deterministic execution guarantees.

Tests that NodeReducer maintains determinism:
- Same inputs + same initial state produce same outputs
- FSM state transitions are deterministic
- State serialization produces identical results
- No hidden sources of entropy

Ticket: OMN-741
"""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType
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
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.nodes.node_reducer import NodeReducer

# Module-level marker for all tests in this file
pytestmark = pytest.mark.unit


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Create simple FSM contract for testing determinism."""
    return ModelFSMSubcontract(
        state_machine_name="determinism_test_fsm",
        description="Test FSM for determinism testing",
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
def multi_path_fsm() -> ModelFSMSubcontract:
    """Create FSM with multiple transition paths for testing determinism."""
    return ModelFSMSubcontract(
        state_machine_name="multi_path_fsm",
        description="FSM with multiple paths for determinism testing",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        version=ModelSemVer(major=1, minor=0, patch=0),
        initial_state="start",
        states=[
            ModelFSMStateDefinition(
                state_name="start",
                state_type="operational",
                description="Initial state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=["init_start"],
                exit_actions=["cleanup_start"],
            ),
            ModelFSMStateDefinition(
                state_name="path_a",
                state_type="operational",
                description="Path A state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=["enter_path_a"],
                exit_actions=["exit_path_a"],
            ),
            ModelFSMStateDefinition(
                state_name="path_b",
                state_type="operational",
                description="Path B state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=["enter_path_b"],
                exit_actions=["exit_path_b"],
            ),
            ModelFSMStateDefinition(
                state_name="merged",
                state_type="operational",
                description="Merged state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=["enter_merged"],
                exit_actions=["exit_merged"],
            ),
            ModelFSMStateDefinition(
                state_name="done",
                state_type="terminal",
                description="Terminal state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                is_terminal=True,
                is_recoverable=False,
            ),
        ],
        transitions=[
            ModelFSMStateTransition(
                transition_name="take_path_a",
                from_state="start",
                to_state="path_a",
                trigger="go_a",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="take_path_b",
                from_state="start",
                to_state="path_b",
                trigger="go_b",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="merge_from_a",
                from_state="path_a",
                to_state="merged",
                trigger="merge",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="merge_from_b",
                from_state="path_b",
                to_state="merged",
                trigger="merge",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="finish",
                from_state="merged",
                to_state="done",
                trigger="complete",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        terminal_states=["done"],
        error_states=[],
        operations=[],
        persistence_enabled=True,
        recovery_enabled=True,
    )


def _create_input_with_fixed_ids(
    data: list[Any],
    trigger: str,
    operation_id: UUID | None = None,
) -> ModelReducerInput[Any]:
    """Create input with deterministic operation ID for consistent testing."""
    return ModelReducerInput(
        data=data,
        reduction_type=EnumReductionType.AGGREGATE,
        operation_id=operation_id or uuid4(),
        metadata={"trigger": trigger},
    )


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeReducerDeterministicTransitions:
    """Test that FSM state transitions are deterministic."""

    @pytest.mark.asyncio
    async def test_same_trigger_from_same_state_produces_same_transition(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that the same trigger from the same state always produces the same next state."""
        results: list[str] = []

        # Run the same transition multiple times
        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Execute same transition
            operation_id = UUID("12345678-1234-1234-1234-123456789abc")
            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=operation_id,
            )

            result = await node.process(input_data)
            results.append(getattr(result.metadata, "fsm_state", None))

        # All results should be identical
        assert all(state == "processing" for state in results)
        assert len(set(results)) == 1, f"Got different states: {set(results)}"

    @pytest.mark.asyncio
    async def test_transition_sequence_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that a sequence of transitions produces deterministic state history."""
        histories: list[list[str]] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Execute transition sequence
            states: list[str] = [node.get_current_state() or ""]

            # First transition: idle -> processing
            input1 = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("11111111-1111-1111-1111-111111111111"),
            )
            await node.process(input1)
            states.append(node.get_current_state() or "")

            # Second transition: processing -> completed
            input2 = _create_input_with_fixed_ids(
                data=[4, 5, 6],
                trigger="complete_event",
                operation_id=UUID("22222222-2222-2222-2222-222222222222"),
            )
            await node.process(input2)
            states.append(node.get_current_state() or "")

            histories.append(states)

        # All histories should be identical
        expected_history = ["idle", "processing", "completed"]
        for history in histories:
            assert history == expected_history, (
                f"Expected {expected_history}, got {history}"
            )

    @pytest.mark.asyncio
    async def test_entry_exit_actions_execute_in_deterministic_order(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that entry/exit actions execute in a deterministic order."""
        all_intents: list[list[str]] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Execute transition that triggers entry/exit actions
            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("33333333-3333-3333-3333-333333333333"),
            )
            result = await node.process(input_data)

            # Extract action-related intents
            action_intents = [
                intent.payload.get("action_name", "")
                for intent in result.intents
                if intent.intent_type == "fsm_state_action"
            ]
            all_intents.append(action_intents)

        # All action sequences should be identical
        assert len(all_intents) > 0
        for intent_sequence in all_intents:
            assert intent_sequence == all_intents[0], (
                f"Action order varies: {all_intents}"
            )

    @pytest.mark.asyncio
    async def test_multi_path_fsm_determinism(
        self,
        test_container: ModelONEXContainer,
        multi_path_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test determinism when FSM has multiple possible paths."""
        # Test path A
        path_a_results: list[list[str]] = []
        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = multi_path_fsm
            node.initialize_fsm_state(multi_path_fsm, context={})

            states: list[str] = [node.get_current_state() or ""]

            # Take path A
            await node.process(
                _create_input_with_fixed_ids(
                    data=[1],
                    trigger="go_a",
                    operation_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                )
            )
            states.append(node.get_current_state() or "")

            # Merge
            await node.process(
                _create_input_with_fixed_ids(
                    data=[2],
                    trigger="merge",
                    operation_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                )
            )
            states.append(node.get_current_state() or "")

            path_a_results.append(states)

        # All path A traversals should be identical
        expected_path_a = ["start", "path_a", "merged"]
        for result in path_a_results:
            assert result == expected_path_a, f"Path A varied: {path_a_results}"

        # Test path B independently
        path_b_results: list[list[str]] = []
        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = multi_path_fsm
            node.initialize_fsm_state(multi_path_fsm, context={})

            states = [node.get_current_state() or ""]

            # Take path B
            await node.process(
                _create_input_with_fixed_ids(
                    data=[1],
                    trigger="go_b",
                    operation_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                )
            )
            states.append(node.get_current_state() or "")

            # Merge
            await node.process(
                _create_input_with_fixed_ids(
                    data=[2],
                    trigger="merge",
                    operation_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
                )
            )
            states.append(node.get_current_state() or "")

            path_b_results.append(states)

        # All path B traversals should be identical
        expected_path_b = ["start", "path_b", "merged"]
        for result in path_b_results:
            assert result == expected_path_b, f"Path B varied: {path_b_results}"


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeReducerDeterministicOutput:
    """Test that same inputs produce same outputs."""

    @pytest.mark.asyncio
    async def test_same_input_produces_same_output_structure(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that identical inputs produce structurally identical outputs."""
        outputs: list[dict[str, Any]] = []
        fixed_operation_id = UUID("44444444-4444-4444-4444-444444444444")

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[10, 20, 30],
                trigger="start_event",
                operation_id=fixed_operation_id,
            )
            result = await node.process(input_data)

            # Extract deterministic fields (exclude timing and timestamps)
            output_snapshot = {
                "fsm_state": getattr(result.metadata, "fsm_state", None),
                "fsm_transition": getattr(result.metadata, "fsm_transition", None),
                "fsm_success": getattr(result.metadata, "fsm_success", None),
                "operation_id": str(result.operation_id),
                "reduction_type": result.reduction_type.value,
                "items_processed": result.items_processed,
                "result": result.result,
            }
            outputs.append(output_snapshot)

        # All outputs should have identical deterministic fields
        for output in outputs:
            assert output == outputs[0], f"Output varies: {outputs}"

    @pytest.mark.asyncio
    async def test_same_data_produces_same_result(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that the same input data produces the same result data."""
        results: list[list[int]] = []
        input_data_list = [100, 200, 300, 400, 500]

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=input_data_list,
                trigger="start_event",
                operation_id=UUID("55555555-5555-5555-5555-555555555555"),
            )
            result = await node.process(input_data)

            # NodeReducer passes through data unchanged
            results.append(list(result.result))

        # All results should be identical
        for result_data in results:
            assert result_data == input_data_list, f"Result data varies: {results}"

    @pytest.mark.asyncio
    async def test_multiple_invocations_produce_identical_results(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that multiple sequential invocations produce identical results."""
        # Use single node instance for multiple invocations
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        first_input = _create_input_with_fixed_ids(
            data=[1, 2, 3],
            trigger="start_event",
            operation_id=UUID("66666666-6666-6666-6666-666666666666"),
        )
        first_result = await node.process(first_input)

        # Create fresh node with same setup
        node2 = NodeReducer(test_container)
        node2.fsm_contract = simple_fsm
        node2.initialize_fsm_state(simple_fsm, context={})

        second_input = _create_input_with_fixed_ids(
            data=[1, 2, 3],
            trigger="start_event",
            operation_id=UUID("66666666-6666-6666-6666-666666666666"),
        )
        second_result = await node2.process(second_input)

        # Compare deterministic fields
        assert getattr(first_result.metadata, "fsm_state", None) == getattr(
            second_result.metadata, "fsm_state", None
        )
        assert getattr(first_result.metadata, "fsm_transition", None) == getattr(
            second_result.metadata, "fsm_transition", None
        )
        assert getattr(first_result.metadata, "fsm_success", None) == getattr(
            second_result.metadata, "fsm_success", None
        )
        assert first_result.result == second_result.result
        assert first_result.items_processed == second_result.items_processed

    @pytest.mark.asyncio
    async def test_intent_count_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that the number and types of intents are deterministic."""
        intent_snapshots: list[list[tuple[str, str]]] = []

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("77777777-7777-7777-7777-777777777777"),
            )
            result = await node.process(input_data)

            # Extract intent types and targets (deterministic properties)
            intent_info = [
                (intent.intent_type, intent.target) for intent in result.intents
            ]
            intent_snapshots.append(intent_info)

        # All intent snapshots should be identical
        for snapshot in intent_snapshots:
            assert snapshot == intent_snapshots[0], f"Intents vary: {intent_snapshots}"


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeReducerStateSerializationDeterminism:
    """Test that state serialization produces identical behavior."""

    @pytest.mark.asyncio
    async def test_serialize_restore_produces_same_behavior(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that serializing and restoring FSM state produces same behavior."""
        # Create initial node and perform transition
        node1 = NodeReducer(test_container)
        node1.fsm_contract = simple_fsm
        node1.initialize_fsm_state(simple_fsm, context={"session_id": "test123"})

        # Perform first transition
        await node1.process(
            _create_input_with_fixed_ids(
                data=[1],
                trigger="start_event",
                operation_id=UUID("88888888-8888-8888-8888-888888888888"),
            )
        )

        # Capture state after first transition
        state_after_first = node1.get_current_state()
        history_after_first = node1.get_state_history()

        # Create second node and restore to same state
        node2 = NodeReducer(test_container)
        node2.fsm_contract = simple_fsm
        # Initialize to processing state (simulating restored state)
        node2.initialize_fsm_state(simple_fsm, context={"session_id": "test123"})
        # Manually set state to match node1
        await node2.execute_fsm_transition(
            simple_fsm, "start_event", {"session_id": "test123"}
        )

        assert node2.get_current_state() == state_after_first

        # Both nodes should now behave identically for next transition
        result1 = await node1.process(
            _create_input_with_fixed_ids(
                data=[2],
                trigger="complete_event",
                operation_id=UUID("99999999-9999-9999-9999-999999999999"),
            )
        )
        result2 = await node2.process(
            _create_input_with_fixed_ids(
                data=[2],
                trigger="complete_event",
                operation_id=UUID("99999999-9999-9999-9999-999999999999"),
            )
        )

        assert getattr(result1.metadata, "fsm_state", None) == getattr(
            result2.metadata, "fsm_state", None
        )
        assert getattr(result1.metadata, "fsm_transition", None) == getattr(
            result2.metadata, "fsm_transition", None
        )

    @pytest.mark.asyncio
    async def test_state_history_is_preserved_correctly(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that state history is preserved correctly across transitions."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm
        node.initialize_fsm_state(simple_fsm, context={})

        # Verify initial history is empty
        assert node.get_state_history() == []

        # First transition
        await node.process(
            _create_input_with_fixed_ids(
                data=[1],
                trigger="start_event",
                operation_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-111111111111"),
            )
        )

        # History should contain initial state
        history_after_first = node.get_state_history()
        assert history_after_first == ["idle"]

        # Second transition
        await node.process(
            _create_input_with_fixed_ids(
                data=[2],
                trigger="complete_event",
                operation_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-222222222222"),
            )
        )

        # History should contain both previous states
        history_after_second = node.get_state_history()
        assert history_after_second == ["idle", "processing"]

    @pytest.mark.asyncio
    async def test_context_data_is_preserved(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that context data is preserved correctly in FSM state."""
        node = NodeReducer(test_container)
        node.fsm_contract = simple_fsm

        initial_context = {"user_id": "user123", "request_id": "req456"}
        node.initialize_fsm_state(simple_fsm, context=initial_context)

        # The context should be available (via internal FSM state)
        # Perform transition to verify context flows through
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={"trigger": "start_event", **initial_context},
        )

        result = await node.process(input_data)

        # Verify context fields appear in output metadata (stored as extra fields)
        # Since ModelReducerMetadata uses extra="allow", custom fields are accessible as attributes
        assert getattr(result.metadata, "user_id", None) == "user123"
        assert getattr(result.metadata, "request_id", None) == "req456"


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeReducerNoHiddenEntropy:
    """Test that no hidden entropy sources affect state transitions."""

    @pytest.mark.asyncio
    async def test_no_random_values_in_transition_metadata(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that FSM transitions do not introduce random values in metadata."""
        metadata_snapshots: list[dict[str, str]] = []

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-111111111111"),
            )
            result = await node.process(input_data)

            # Extract FSM-related metadata (exclude trigger which is input)
            fsm_metadata = {
                "fsm_state": getattr(result.metadata, "fsm_state", None),
                "fsm_transition": getattr(result.metadata, "fsm_transition", None),
                "fsm_success": getattr(result.metadata, "fsm_success", None),
            }
            metadata_snapshots.append(fsm_metadata)

        # All metadata snapshots should be identical
        for snapshot in metadata_snapshots:
            assert snapshot == metadata_snapshots[0], (
                f"Metadata varies: {metadata_snapshots}"
            )

    @pytest.mark.asyncio
    async def test_intent_generation_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that intent generation produces deterministic results (excluding UUIDs)."""
        intent_structures: list[list[dict[str, Any]]] = []

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("cccccccc-cccc-cccc-cccc-111111111111"),
            )
            result = await node.process(input_data)

            # Extract intent structure (excluding auto-generated intent_id)
            intent_list = [
                {
                    "intent_type": intent.intent_type,
                    "target": intent.target,
                    "priority": intent.priority,
                    # Payload structure but exclude any timestamps
                    "payload_keys": sorted(intent.payload.keys()),
                }
                for intent in result.intents
            ]
            intent_structures.append(intent_list)

        # All intent structures should be identical
        for structure in intent_structures:
            assert structure == intent_structures[0], (
                f"Intent structures vary: {intent_structures}"
            )

    @pytest.mark.asyncio
    async def test_intent_ordering_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        multi_path_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that intents are emitted in a deterministic order."""
        intent_orders: list[list[str]] = []

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = multi_path_fsm
            node.initialize_fsm_state(multi_path_fsm, context={})

            # This transition has entry/exit actions
            input_data = _create_input_with_fixed_ids(
                data=[1],
                trigger="go_a",
                operation_id=UUID("dddddddd-dddd-dddd-dddd-111111111111"),
            )
            result = await node.process(input_data)

            # Record intent types in order
            intent_order = [intent.intent_type for intent in result.intents]
            intent_orders.append(intent_order)

        # All intent orders should be identical
        for order in intent_orders:
            assert order == intent_orders[0], f"Intent order varies: {intent_orders}"

    @pytest.mark.asyncio
    async def test_items_processed_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that items_processed count is deterministic."""
        counts: list[int] = []
        test_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=test_data,
                trigger="start_event",
                operation_id=UUID("eeeeeeee-eeee-eeee-eeee-111111111111"),
            )
            result = await node.process(input_data)
            counts.append(result.items_processed)

        # All counts should be identical
        assert all(count == len(test_data) for count in counts)
        assert len(set(counts)) == 1, f"Item counts vary: {set(counts)}"

    @pytest.mark.asyncio
    async def test_batches_processed_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that batches_processed count is deterministic."""
        batch_counts: list[int] = []

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("ffffffff-ffff-ffff-ffff-111111111111"),
            )
            result = await node.process(input_data)
            batch_counts.append(result.batches_processed)

        # All batch counts should be identical (should be 1 for single input)
        assert all(count == 1 for count in batch_counts)

    @pytest.mark.asyncio
    async def test_conflicts_resolved_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that conflicts_resolved count is deterministic."""
        conflict_counts: list[int] = []

        for _ in range(5):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[1, 2, 3],
                trigger="start_event",
                operation_id=UUID("11111111-2222-3333-4444-555555555555"),
            )
            result = await node.process(input_data)
            conflict_counts.append(result.conflicts_resolved)

        # All conflict counts should be identical (0 for simple pass-through)
        assert all(count == 0 for count in conflict_counts)


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeReducerDeterministicEdgeCases:
    """Test determinism in edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_data_list_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test determinism with empty data list."""
        results: list[tuple[str, int]] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=[],  # Empty data
                trigger="start_event",
                operation_id=UUID("12121212-1212-1212-1212-121212121212"),
            )
            result = await node.process(input_data)
            results.append(
                (getattr(result.metadata, "fsm_state", None), result.items_processed)
            )

        # All should produce same state and count
        assert all(r == ("processing", 0) for r in results)

    @pytest.mark.asyncio
    async def test_large_data_list_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test determinism with large data list."""
        large_data = list(range(1000))
        results: list[tuple[str, int]] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=large_data,
                trigger="start_event",
                operation_id=UUID("13131313-1313-1313-1313-131313131313"),
            )
            result = await node.process(input_data)
            results.append(
                (getattr(result.metadata, "fsm_state", None), result.items_processed)
            )

        # All should produce same state and count
        assert all(r == ("processing", 1000) for r in results)

    @pytest.mark.asyncio
    async def test_complex_nested_data_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test determinism with complex nested data structures."""
        complex_data = [
            {"id": 1, "nested": {"values": [1, 2, 3]}, "tags": ["a", "b"]},
            {"id": 2, "nested": {"values": [4, 5, 6]}, "tags": ["c", "d"]},
        ]
        results: list[list[dict[str, Any]]] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_input_with_fixed_ids(
                data=complex_data,
                trigger="start_event",
                operation_id=UUID("14141414-1414-1414-1414-141414141414"),
            )
            result = await node.process(input_data)
            # Deep copy to ensure we capture the exact state
            results.append(copy.deepcopy(result.result))

        # All results should be identical
        for result_data in results:
            assert result_data == complex_data

    @pytest.mark.asyncio
    async def test_terminal_state_detection_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that terminal state detection is deterministic."""
        terminal_states: list[bool] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Not terminal initially
            assert not node.is_complete()

            # Transition to processing
            await node.process(
                _create_input_with_fixed_ids(
                    data=[1],
                    trigger="start_event",
                    operation_id=UUID("15151515-1515-1515-1515-151515151515"),
                )
            )
            assert not node.is_complete()

            # Transition to completed (terminal)
            await node.process(
                _create_input_with_fixed_ids(
                    data=[2],
                    trigger="complete_event",
                    operation_id=UUID("16161616-1616-1616-1616-161616161616"),
                )
            )
            terminal_states.append(node.is_complete())

        # All should detect terminal state
        assert all(is_terminal for is_terminal in terminal_states)

    @pytest.mark.asyncio
    async def test_fsm_state_snapshot_is_deterministic(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Test that FSM state snapshots are deterministic."""
        snapshots: list[tuple[str | None, list[str]]] = []

        for _ in range(3):
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Perform transition sequence
            await node.process(
                _create_input_with_fixed_ids(
                    data=[1],
                    trigger="start_event",
                    operation_id=UUID("17171717-1717-1717-1717-171717171717"),
                )
            )
            await node.process(
                _create_input_with_fixed_ids(
                    data=[2],
                    trigger="complete_event",
                    operation_id=UUID("18181818-1818-1818-1818-181818181818"),
                )
            )

            # Capture final snapshot
            snapshots.append((node.get_current_state(), node.get_state_history()))

        # All snapshots should be identical
        expected_snapshot = ("completed", ["idle", "processing"])
        for snapshot in snapshots:
            assert snapshot == expected_snapshot, f"Snapshot varies: {snapshots}"
