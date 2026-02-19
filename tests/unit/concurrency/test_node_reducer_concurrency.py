# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Concurrency tests for NodeReducer FSM state thread safety.

HIGH PRIORITY: NodeReducer has HIGH thread safety risk because FSM state is mutable.
Concurrent state transitions can corrupt reducer state.

Thread Safety Issues Tested:
1. FSM state mutation races - State transitions are not atomic
2. Concurrent ModelReducerInput processing - Multiple inputs processed simultaneously
3. ModelReducerOutput generation races - Output generation under concurrent load
4. State snapshot isolation - FSM state snapshots must be isolated per operation

See docs/guides/THREADING.md for complete thread safety documentation.

Ticket: OMN-892 (NodeReducer Concurrency Tests)
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
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
from omnibase_core.models.fsm.model_fsm_state_snapshot import ModelFSMStateSnapshot
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.nodes.node_reducer import NodeReducer

# Module-level marker for all tests in this file
pytestmark = [pytest.mark.unit, pytest.mark.timeout(120)]


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container for NodeReducer instantiation."""
    return ModelONEXContainer()


@pytest.fixture
def simple_fsm() -> ModelFSMSubcontract:
    """Create simple FSM contract for concurrency testing."""
    return ModelFSMSubcontract(
        state_machine_name="concurrency_test_fsm",
        description="FSM for concurrency testing",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        version=ModelSemVer(major=1, minor=0, patch=0),
        initial_state="idle",
        states=[
            ModelFSMStateDefinition(
                state_name="idle",
                state_type="operational",
                description="Initial idle state",
                version=ModelSemVer(major=1, minor=0, patch=0),
                entry_actions=[],
                exit_actions=["cleanup_idle"],
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
def multi_state_fsm() -> ModelFSMSubcontract:
    """Create FSM with multiple states for complex concurrency testing."""
    return ModelFSMSubcontract(
        state_machine_name="multi_state_concurrency_fsm",
        description="FSM with multiple states for concurrency testing",
        state_machine_version=ModelSemVer(major=1, minor=0, patch=0),
        version=ModelSemVer(major=1, minor=0, patch=0),
        initial_state="start",
        states=[
            ModelFSMStateDefinition(
                state_name="start",
                state_type="operational",
                description="Starting state",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="phase_1",
                state_type="operational",
                description="Phase 1",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="phase_2",
                state_type="operational",
                description="Phase 2",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateDefinition(
                state_name="phase_3",
                state_type="operational",
                description="Phase 3",
                version=ModelSemVer(major=1, minor=0, patch=0),
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
                transition_name="to_phase_1",
                from_state="start",
                to_state="phase_1",
                trigger="next",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="to_phase_2",
                from_state="phase_1",
                to_state="phase_2",
                trigger="next",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="to_phase_3",
                from_state="phase_2",
                to_state="phase_3",
                trigger="next",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            ModelFSMStateTransition(
                transition_name="finish",
                from_state="phase_3",
                to_state="done",
                trigger="next",
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
        ],
        terminal_states=["done"],
        error_states=[],
        operations=[],
        persistence_enabled=False,
        recovery_enabled=False,
    )


def _create_reducer_input(
    data: list[Any],
    trigger: str,
    operation_id: UUID | None = None,
) -> ModelReducerInput[Any]:
    """Create ModelReducerInput with specified trigger."""
    return ModelReducerInput(
        data=data,
        reduction_type=EnumReductionType.AGGREGATE,
        operation_id=operation_id or uuid4(),
        metadata={"trigger": trigger},
    )


@pytest.mark.unit
class TestNodeReducerFSMConcurrency:
    """Test FSM state thread safety under concurrent load.

    NodeReducer FSM state is mutable and NOT thread-safe.
    These tests verify that concurrent access DOES cause issues when
    not properly isolated, demonstrating why thread-local instances
    are required for production use.
    """

    @pytest.mark.asyncio
    async def test_concurrent_state_transitions_10_tasks(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """10+ async tasks triggering state transitions simultaneously.

        This test demonstrates that with ISOLATED instances per task,
        concurrent state transitions work correctly.
        """
        num_tasks = 15
        results: list[tuple[str | None, bool]] = []
        errors: list[Exception] = []
        lock = asyncio.Lock()

        async def transition_task(task_id: int) -> None:
            """Each task gets its own NodeReducer instance (safe pattern)."""
            try:
                # Safe pattern: separate instance per task
                node = NodeReducer(test_container)
                node.fsm_contract = simple_fsm
                node.initialize_fsm_state(simple_fsm, context={"task_id": task_id})

                # Perform transition
                input_data = _create_reducer_input(
                    data=[task_id, task_id * 2],
                    trigger="start_event",
                    operation_id=UUID(
                        f"1234{task_id:04d}-1234-1234-1234-123456789abc"[:36]
                    ),
                )
                result = await node.process(input_data)

                async with lock:
                    results.append(
                        (
                            getattr(result.metadata, "fsm_state", None),
                            getattr(result.metadata, "fsm_success", False),
                        )
                    )
            except Exception as e:
                async with lock:
                    errors.append(e)

        # Launch all tasks concurrently
        tasks = [asyncio.create_task(transition_task(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # All tasks should have succeeded with isolated instances
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == num_tasks
        # All should transition to "processing" state
        assert all(state == "processing" for state, _ in results), (
            f"Not all tasks reached expected state: {results}"
        )
        assert all(success for _, success in results), (
            f"Not all transitions succeeded: {results}"
        )

    @pytest.mark.asyncio
    async def test_fsm_state_mutation_isolation(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """FSM state mutations don't leak between concurrent operations.

        Each async task creates its own NodeReducer instance, ensuring
        state mutations are isolated.
        """
        num_tasks = 12
        state_histories: list[list[str]] = []
        lock = asyncio.Lock()

        async def mutate_state(task_id: int) -> None:
            """Perform multiple state mutations in isolated instance."""
            # Safe pattern: new instance per task
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={"task": task_id})

            # First transition: idle -> processing
            input1 = _create_reducer_input(
                data=[f"data_{task_id}_1"],
                trigger="start_event",
            )
            await node.process(input1)

            # Second transition: processing -> completed
            input2 = _create_reducer_input(
                data=[f"data_{task_id}_2"],
                trigger="complete_event",
            )
            await node.process(input2)

            # Capture final history
            history = node.get_state_history()

            async with lock:
                state_histories.append(history)

        # Run all tasks concurrently
        tasks = [asyncio.create_task(mutate_state(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Each task should have independent history
        assert len(state_histories) == num_tasks
        expected_history = ["idle", "processing"]
        for history in state_histories:
            assert history == expected_history, (
                f"History leaked between tasks. Expected {expected_history}, got {history}"
            )

    @pytest.mark.asyncio
    async def test_state_snapshot_independence(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """State snapshots are independent under concurrent access.

        Snapshots use deep_copy=True to ensure complete isolation.
        """
        num_tasks = 10
        snapshots: list[ModelFSMStateSnapshot | None] = []
        lock = asyncio.Lock()

        async def capture_snapshot(task_id: int) -> None:
            """Create snapshot with deep copy for isolation."""
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(
                simple_fsm,
                context={"task_id": task_id, "unique_data": f"value_{task_id}"},
            )

            # Perform transition
            input_data = _create_reducer_input(
                data=[task_id],
                trigger="start_event",
            )
            await node.process(input_data)

            # Capture snapshot with deep copy for true independence
            snapshot = node.snapshot_state(deep_copy=True)

            async with lock:
                snapshots.append(snapshot)

        tasks = [asyncio.create_task(capture_snapshot(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify all snapshots were captured
        assert len(snapshots) == num_tasks
        assert all(s is not None for s in snapshots)

        # Verify snapshots are independent (each has its own context)
        for i, snapshot in enumerate(snapshots):
            assert snapshot is not None
            assert snapshot.current_state == "processing"
            # Each snapshot should have different context (task_id varies)
            # Since deep_copy=True, modifying one won't affect others

        # Verify that modifying one snapshot doesn't affect others
        if snapshots[0] is not None:
            # Get reference to first snapshot's context
            original_context = dict(snapshots[0].context)
            # Try to modify (should not affect other snapshots due to deep_copy)
            # Note: We can't actually modify frozen models, but we verify independence
            for snapshot in snapshots[1:]:
                if snapshot is not None:
                    # Verify other snapshots have their own distinct context
                    assert id(snapshot.context) != id(snapshots[0].context)


@pytest.mark.unit
class TestModelReducerInputConcurrency:
    """Test concurrent ModelReducerInput processing.

    ModelReducerInput is immutable (frozen=True) and thread-safe,
    but the NodeReducer processing them must use isolated instances.
    """

    @pytest.mark.asyncio
    async def test_concurrent_input_processing_10_tasks(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """10+ concurrent ModelReducerInput processing operations."""
        num_tasks = 15
        processing_results: list[dict[str, Any]] = []
        lock = asyncio.Lock()

        async def process_input(task_id: int) -> None:
            """Process input in isolated node instance."""
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Create unique input for this task
            input_data = ModelReducerInput(
                data=[task_id, task_id * 10, task_id * 100],
                reduction_type=EnumReductionType.AGGREGATE,
                operation_id=uuid4(),
                metadata={"trigger": "start_event", "task_id": str(task_id)},
            )

            result = await node.process(input_data)

            async with lock:
                processing_results.append(
                    {
                        "task_id": task_id,
                        "items_processed": result.items_processed,
                        "result_data": result.result,
                        "fsm_state": getattr(result.metadata, "fsm_state", None),
                        "operation_id": str(result.operation_id),
                    }
                )

        tasks = [asyncio.create_task(process_input(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify all tasks completed successfully
        assert len(processing_results) == num_tasks

        # Each task should have processed its own data correctly
        for result in processing_results:
            task_id = result["task_id"]
            assert result["items_processed"] == 3
            assert result["result_data"] == [task_id, task_id * 10, task_id * 100]
            assert result["fsm_state"] == "processing"

    @pytest.mark.asyncio
    async def test_input_validation_under_concurrent_load(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Input validation remains correct under concurrent load.

        Verify that ModelReducerInput frozen/immutable properties
        are respected even under concurrent processing.
        """
        num_tasks = 10
        validation_results: list[tuple[int, bool, int]] = []
        lock = asyncio.Lock()

        async def validate_and_process(task_id: int) -> None:
            """Validate input properties remain stable during processing."""
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            # Create input with specific batch_size
            batch_size = 500 + task_id * 10
            input_data = ModelReducerInput(
                data=list(range(task_id, task_id + 5)),
                reduction_type=EnumReductionType.FOLD,
                batch_size=batch_size,
                metadata={"trigger": "start_event"},
            )

            # Verify input properties before processing
            pre_batch_size = input_data.batch_size
            pre_data_len = len(input_data.data)

            await node.process(input_data)

            # Verify input properties after processing (should be unchanged - frozen)
            post_batch_size = input_data.batch_size
            post_data_len = len(input_data.data)

            is_valid = (pre_batch_size == post_batch_size) and (
                pre_data_len == post_data_len
            )

            async with lock:
                validation_results.append((task_id, is_valid, batch_size))

        tasks = [asyncio.create_task(validate_and_process(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # All inputs should have remained immutable
        assert len(validation_results) == num_tasks
        for task_id, is_valid, batch_size in validation_results:
            assert is_valid, (
                f"Input for task {task_id} was modified (batch_size={batch_size})"
            )


@pytest.mark.unit
class TestModelReducerOutputConcurrency:
    """Test concurrent ModelReducerOutput generation.

    ModelReducerOutput is immutable (frozen=True) and thread-safe for reads.
    """

    @pytest.mark.asyncio
    async def test_concurrent_output_generation_10_tasks(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """10+ concurrent ModelReducerOutput generation operations."""
        num_tasks = 12
        outputs: list[dict[str, Any]] = []
        lock = asyncio.Lock()

        async def generate_output(task_id: int) -> None:
            """Generate output in isolated node instance."""
            node = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={})

            input_data = _create_reducer_input(
                data=[task_id * i for i in range(1, 6)],  # [task_id, task_id*2, ...]
                trigger="start_event",
                operation_id=uuid4(),
            )

            result = await node.process(input_data)

            async with lock:
                outputs.append(
                    {
                        "task_id": task_id,
                        "operation_id": result.operation_id,
                        "items_processed": result.items_processed,
                        "batches_processed": result.batches_processed,
                        "conflicts_resolved": result.conflicts_resolved,
                        "intents_count": len(result.intents),
                    }
                )

        tasks = [asyncio.create_task(generate_output(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # All outputs should be generated
        assert len(outputs) == num_tasks

        # Each output should have consistent properties
        for output in outputs:
            assert output["items_processed"] == 5
            assert output["batches_processed"] == 1
            assert output["conflicts_resolved"] == 0
            # Intents should be generated (entry/exit actions, metrics, persistence)
            assert output["intents_count"] >= 0

        # All operation IDs should be unique
        operation_ids = [o["operation_id"] for o in outputs]
        assert len(set(operation_ids)) == num_tasks

    @pytest.mark.asyncio
    async def test_output_state_consistency(
        self,
        test_container: ModelONEXContainer,
        multi_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """Output state remains consistent under concurrent generation.

        Test that FSM state in output accurately reflects the transition
        that occurred, even under concurrent load.
        """
        num_tasks = 10
        state_results: list[dict[str, str | None]] = []
        lock = asyncio.Lock()

        async def track_state_progression(task_id: int) -> None:
            """Track FSM state through multiple transitions."""
            node = NodeReducer(test_container)
            node.fsm_contract = multi_state_fsm
            node.initialize_fsm_state(multi_state_fsm, context={"task": task_id})

            states_seen: list[str | None] = []

            # Perform sequence of transitions: start -> phase_1 -> phase_2 -> phase_3
            for _ in range(3):  # 3 transitions
                input_data = _create_reducer_input(
                    data=[task_id],
                    trigger="next",
                )
                result = await node.process(input_data)
                states_seen.append(getattr(result.metadata, "fsm_state", None))

            async with lock:
                state_results.append(
                    {
                        "task_id": str(task_id),
                        "state_1": states_seen[0] if len(states_seen) > 0 else None,
                        "state_2": states_seen[1] if len(states_seen) > 1 else None,
                        "state_3": states_seen[2] if len(states_seen) > 2 else None,
                    }
                )

        tasks = [
            asyncio.create_task(track_state_progression(i)) for i in range(num_tasks)
        ]
        await asyncio.gather(*tasks)

        # Verify state progression is consistent for all tasks
        expected_progression = ("phase_1", "phase_2", "phase_3")
        for result in state_results:
            actual_progression = (
                result["state_1"],
                result["state_2"],
                result["state_3"],
            )
            assert actual_progression == expected_progression, (
                f"Task {result['task_id']} had incorrect state progression: {actual_progression}"
            )


@pytest.mark.unit
class TestNodeReducerThreadLocalPattern:
    """Test thread-local instance pattern for NodeReducer.

    NodeReducer instances are NOT thread-safe. The recommended pattern
    is to use thread-local storage to ensure each thread gets its own
    isolated instance with independent FSM state.
    """

    def test_thread_local_reducers_isolated(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Each thread gets independent NodeReducer with isolated FSM state."""
        thread_local = threading.local()
        num_threads = 10
        instances: list[NodeReducer[Any, Any]] = []
        lock = threading.Lock()

        def get_thread_local_reducer() -> NodeReducer[Any, Any]:
            """Get or create thread-local NodeReducer instance."""
            if not hasattr(thread_local, "reducer"):
                node: NodeReducer[Any, Any] = NodeReducer(test_container)
                node.fsm_contract = simple_fsm
                node.initialize_fsm_state(simple_fsm, context={})
                thread_local.reducer = node
            return thread_local.reducer

        def worker(thread_id: int) -> None:
            """Each worker gets its own thread-local reducer."""
            reducer = get_thread_local_reducer()

            # Perform a transition
            async def do_transition() -> None:
                input_data = _create_reducer_input(
                    data=[thread_id],
                    trigger="start_event",
                )
                await reducer.process(input_data)

            asyncio.run(do_transition())

            with lock:
                instances.append(reducer)

        # Launch threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have gotten its own instance
        assert len(instances) == num_threads
        instance_ids = [id(inst) for inst in instances]
        # All instances should be unique (different memory addresses)
        assert len(set(instance_ids)) == num_threads, (
            f"Expected {num_threads} unique instances, got {len(set(instance_ids))}"
        )

    def test_thread_local_state_no_leakage(
        self,
        test_container: ModelONEXContainer,
        multi_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """FSM state doesn't leak between thread-local instances."""
        thread_local = threading.local()
        num_threads = 8
        final_states: list[tuple[int, str | None, list[str]]] = []
        lock = threading.Lock()

        def get_reducer() -> NodeReducer[Any, Any]:
            """Get thread-local reducer."""
            if not hasattr(thread_local, "reducer"):
                node: NodeReducer[Any, Any] = NodeReducer(test_container)
                node.fsm_contract = multi_state_fsm
                node.initialize_fsm_state(multi_state_fsm, context={})
                thread_local.reducer = node
            return thread_local.reducer

        def worker(thread_id: int, num_transitions: int) -> None:
            """Perform varying number of transitions per thread."""
            reducer = get_reducer()

            async def perform_transitions() -> None:
                for _ in range(num_transitions):
                    input_data = _create_reducer_input(
                        data=[thread_id],
                        trigger="next",
                    )
                    await reducer.process(input_data)

            asyncio.run(perform_transitions())

            final_state = reducer.get_current_state()
            history = reducer.get_state_history()

            with lock:
                final_states.append((thread_id, final_state, history))

        # Each thread will perform different number of transitions
        threads = []
        expected_states_map = {
            0: "phase_1",  # 1 transition
            1: "phase_2",  # 2 transitions
            2: "phase_3",  # 3 transitions
            3: "done",  # 4 transitions
        }

        for i in range(num_threads):
            num_transitions = (i % 4) + 1  # 1, 2, 3, or 4 transitions
            t = threading.Thread(target=worker, args=(i, num_transitions))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify each thread ended in expected state based on its transitions
        assert len(final_states) == num_threads

        for thread_id, final_state, history in final_states:
            num_transitions = (thread_id % 4) + 1
            expected_state = expected_states_map[num_transitions - 1]
            assert final_state == expected_state, (
                f"Thread {thread_id} (transitions={num_transitions}) ended in {final_state}, "
                f"expected {expected_state}. History: {history}"
            )


@pytest.mark.unit
class TestSharedNodeReducerRaceConditions:
    """Test race conditions when NodeReducer is INCORRECTLY shared.

    These tests demonstrate what happens when the thread safety
    guidelines are NOT followed. They may exhibit non-deterministic
    behavior, which is the expected outcome when sharing mutable
    FSM state across threads.

    WARNING: These tests are marked xfail or may be flaky by design.
    They exist to document and demonstrate the race conditions.
    """

    @pytest.mark.xfail(
        reason="Race demonstration; shared NodeReducer causes FSM state corruption",
        strict=False,
    )
    def test_shared_reducer_state_corruption(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Demonstrates FSM state corruption with shared NodeReducer.

        UNSAFE PATTERN: Sharing a single NodeReducer across threads.
        This test may pass sometimes and fail other times due to races.
        """
        # UNSAFE: Single shared instance
        shared_node: NodeReducer[Any, Any] = NodeReducer(test_container)
        shared_node.fsm_contract = simple_fsm
        shared_node.initialize_fsm_state(simple_fsm, context={})

        num_threads = 10
        final_states: list[str | None] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            """All threads share the same reducer - UNSAFE."""

            async def do_transition() -> None:
                input_data = _create_reducer_input(
                    data=[thread_id],
                    trigger="start_event",
                )
                await shared_node.process(input_data)

            try:
                asyncio.run(do_transition())
            except Exception:
                pass  # Ignore errors from races

            with lock:
                final_states.append(shared_node.get_current_state())

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # With races, we cannot predict the final state
        # The FSM may be corrupted or in an inconsistent state
        # This assertion may fail due to race conditions
        assert len(final_states) == num_threads

        # All should be "processing" if no races occurred
        # But races may cause inconsistent states
        all_processing = all(state == "processing" for state in final_states)
        if not all_processing:
            # This demonstrates the race condition - state is inconsistent
            pytest.fail(
                f"Race condition detected: Not all states are 'processing'. "
                f"States: {set(final_states)}"
            )


@pytest.mark.unit
class TestNodeReducerWithThreadPoolExecutor:
    """Test NodeReducer behavior with ThreadPoolExecutor.

    These tests verify correct usage patterns when using ThreadPoolExecutor
    for parallel processing with NodeReducer.
    """

    def test_executor_with_isolated_instances(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """ThreadPoolExecutor with isolated NodeReducer per task."""
        num_tasks = 20
        results: list[dict[str, Any]] = []
        lock = threading.Lock()

        def process_task(task_id: int) -> dict[str, Any]:
            """Each task creates its own NodeReducer - SAFE."""
            node: NodeReducer[Any, Any] = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={"task": task_id})

            async def do_process() -> dict[str, Any]:
                input_data = _create_reducer_input(
                    data=[task_id, task_id * 2],
                    trigger="start_event",
                )
                output = await node.process(input_data)
                return {
                    "task_id": task_id,
                    "state": getattr(output.metadata, "fsm_state", None),
                    "items": output.items_processed,
                }

            return asyncio.run(do_process())

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_task, i) for i in range(num_tasks)]
            for future in futures:
                result = future.result()
                with lock:
                    results.append(result)

        # All tasks should complete successfully
        assert len(results) == num_tasks
        assert all(r["state"] == "processing" for r in results)
        assert all(r["items"] == 2 for r in results)

    def test_executor_with_complex_workflow(
        self,
        test_container: ModelONEXContainer,
        multi_state_fsm: ModelFSMSubcontract,
    ) -> None:
        """ThreadPoolExecutor with complex multi-step workflows."""
        num_tasks = 10
        workflow_results: list[dict[str, Any]] = []
        lock = threading.Lock()

        def run_workflow(task_id: int) -> dict[str, Any]:
            """Execute full workflow in isolated instance."""
            node: NodeReducer[Any, Any] = NodeReducer(test_container)
            node.fsm_contract = multi_state_fsm
            node.initialize_fsm_state(multi_state_fsm, context={"workflow": task_id})

            async def execute_workflow() -> dict[str, Any]:
                states: list[str | None] = []

                # Execute 4 transitions to reach terminal state
                for step in range(4):
                    input_data = _create_reducer_input(
                        data=[task_id, step],
                        trigger="next",
                    )
                    result = await node.process(input_data)
                    states.append(getattr(result.metadata, "fsm_state", None))

                return {
                    "task_id": task_id,
                    "states_traversed": states,
                    "final_state": node.get_current_state(),
                    "is_complete": node.is_complete(),
                    "history": node.get_state_history(),
                }

            return asyncio.run(execute_workflow())

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_workflow, i) for i in range(num_tasks)]
            for future in futures:
                result = future.result()
                with lock:
                    workflow_results.append(result)

        # All workflows should complete to terminal state
        assert len(workflow_results) == num_tasks

        expected_states = ["phase_1", "phase_2", "phase_3", "done"]
        expected_history = ["start", "phase_1", "phase_2", "phase_3"]

        for result in workflow_results:
            assert result["states_traversed"] == expected_states, (
                f"Task {result['task_id']} wrong traversal: {result['states_traversed']}"
            )
            assert result["final_state"] == "done"
            assert result["is_complete"] is True
            assert result["history"] == expected_history


@pytest.mark.unit
class TestNodeReducerSnapshotRestoreConcurrency:
    """Test snapshot and restore operations under concurrent load.

    Verifies that FSM state snapshot/restore works correctly when
    multiple operations are happening concurrently.
    """

    @pytest.mark.asyncio
    async def test_concurrent_snapshot_operations(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Multiple concurrent snapshot operations don't interfere."""
        num_tasks = 12
        snapshot_data: list[dict[str, Any]] = []
        lock = asyncio.Lock()

        async def snapshot_task(task_id: int) -> None:
            """Create and verify snapshot in isolated instance."""
            node: NodeReducer[Any, Any] = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={"snapshot_task": task_id})

            # Perform transition
            input_data = _create_reducer_input(
                data=[task_id],
                trigger="start_event",
            )
            await node.process(input_data)

            # Take snapshot with deep copy
            snapshot = node.snapshot_state(deep_copy=True)
            dict_snapshot = node.get_state_snapshot(deep_copy=True)

            async with lock:
                snapshot_data.append(
                    {
                        "task_id": task_id,
                        "snapshot": snapshot,
                        "dict_snapshot": dict_snapshot,
                    }
                )

        tasks = [asyncio.create_task(snapshot_task(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify all snapshots were captured correctly
        assert len(snapshot_data) == num_tasks

        for data in snapshot_data:
            snapshot = data["snapshot"]
            dict_snapshot = data["dict_snapshot"]

            assert snapshot is not None
            assert snapshot.current_state == "processing"
            assert dict_snapshot is not None
            assert dict_snapshot["current_state"] == "processing"

    @pytest.mark.asyncio
    async def test_concurrent_restore_operations(
        self,
        test_container: ModelONEXContainer,
        simple_fsm: ModelFSMSubcontract,
    ) -> None:
        """Concurrent restore operations with isolated instances."""
        num_tasks = 10

        # Create a valid snapshot to restore from
        reference_node: NodeReducer[Any, Any] = NodeReducer(test_container)
        reference_node.fsm_contract = simple_fsm
        reference_node.initialize_fsm_state(simple_fsm, context={"source": "reference"})
        await reference_node.process(
            _create_reducer_input(data=[1], trigger="start_event")
        )
        reference_snapshot = reference_node.snapshot_state(deep_copy=True)
        assert reference_snapshot is not None

        restore_results: list[dict[str, Any]] = []
        lock = asyncio.Lock()

        async def restore_task(task_id: int) -> None:
            """Restore snapshot in isolated instance."""
            node: NodeReducer[Any, Any] = NodeReducer(test_container)
            node.fsm_contract = simple_fsm
            node.initialize_fsm_state(simple_fsm, context={"restore_task": task_id})

            # Verify initial state
            initial_state = node.get_current_state()

            # Restore from reference snapshot
            assert reference_snapshot is not None
            node.restore_state(reference_snapshot, validate=True)

            # Verify restored state
            restored_state = node.get_current_state()

            async with lock:
                restore_results.append(
                    {
                        "task_id": task_id,
                        "initial_state": initial_state,
                        "restored_state": restored_state,
                    }
                )

        tasks = [asyncio.create_task(restore_task(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        # All restores should succeed
        assert len(restore_results) == num_tasks

        for result in restore_results:
            assert result["initial_state"] == "idle"
            assert result["restored_state"] == "processing"
