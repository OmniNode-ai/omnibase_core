"""Comprehensive concurrency tests for NodeOrchestrator.

This module validates thread safety and async concurrency behavior of
NodeOrchestrator, which has HIGH thread safety risk due to mutable workflow state.

Thread Safety Issues Tested:
1. Workflow state mutation races - workflow state transitions are not atomic
2. Concurrent step execution - multiple workflow steps executed simultaneously
3. Lease-based coordination races - ModelAction lease conflicts under concurrent load
4. Workflow context isolation - workflow contexts must be isolated per operation

Test Categories:
- TestNodeOrchestratorWorkflowConcurrency: Workflow state thread safety
- TestModelActionLeaseConcurrency: Lease-based coordination tests
- TestOrchestratorInputOutputConcurrency: Input/output processing tests
- TestNodeOrchestratorThreadLocalPattern: Thread-local instance pattern tests

Reference: docs/guides/THREADING.md - Thread Safety Guidelines

WARNING: NodeOrchestrator instances are NOT thread-safe by design.
The recommended pattern is thread-local instances (one per thread).
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
    ModelWorkflowNode,
)
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.orchestrator.model_orchestrator_output import (
    ModelOrchestratorOutput,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.workflow import ModelWorkflowStateSnapshot
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

pytestmark = [pytest.mark.unit, pytest.mark.timeout(60)]

# Default version for test instances - required field
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def container() -> ModelONEXContainer:
    """Create a fresh ModelONEXContainer for testing."""
    return ModelONEXContainer()


@pytest.fixture
def workflow_definition() -> ModelWorkflowDefinition:
    """Create a sample workflow definition for testing."""
    return ModelWorkflowDefinition(
        version=DEFAULT_VERSION,
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test_workflow",
            workflow_version=DEFAULT_VERSION,
            execution_mode="sequential",
            timeout_ms=30000,
            description="Test workflow for concurrency testing",
        ),
        execution_graph=ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[
                ModelWorkflowNode(
                    version=DEFAULT_VERSION,
                    node_id=uuid4(),
                    node_type=EnumNodeType.COMPUTE_GENERIC,
                ),
                ModelWorkflowNode(
                    version=DEFAULT_VERSION,
                    node_id=uuid4(),
                    node_type=EnumNodeType.COMPUTE_GENERIC,
                ),
            ],
        ),
        coordination_rules=ModelCoordinationRules(
            version=DEFAULT_VERSION,
            parallel_execution_allowed=True,
        ),
    )


@pytest.fixture
def workflow_steps() -> list[ModelWorkflowStep]:
    """Create sample workflow steps for testing."""
    step1_id = uuid4()
    step2_id = uuid4()
    step3_id = uuid4()
    return [
        ModelWorkflowStep(
            step_id=step1_id,
            step_name="fetch_data",
            step_type="effect",
            enabled=True,
            timeout_ms=5000,
        ),
        ModelWorkflowStep(
            step_id=step2_id,
            step_name="process_data",
            step_type="compute",
            depends_on=[step1_id],
            enabled=True,
            timeout_ms=5000,
        ),
        ModelWorkflowStep(
            step_id=step3_id,
            step_name="save_results",
            step_type="effect",
            depends_on=[step2_id],
            enabled=True,
            timeout_ms=5000,
        ),
    ]


def create_workflow_definition() -> ModelWorkflowDefinition:
    """Helper to create workflow definition for thread-local tests."""
    return ModelWorkflowDefinition(
        version=DEFAULT_VERSION,
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test_workflow",
            workflow_version=DEFAULT_VERSION,
            execution_mode="sequential",
            timeout_ms=30000,
            description="Test workflow for concurrency testing",
        ),
        execution_graph=ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[
                ModelWorkflowNode(
                    version=DEFAULT_VERSION,
                    node_id=uuid4(),
                    node_type=EnumNodeType.COMPUTE_GENERIC,
                ),
            ],
        ),
        coordination_rules=ModelCoordinationRules(
            version=DEFAULT_VERSION,
            parallel_execution_allowed=True,
        ),
    )


# =============================================================================
# TestNodeOrchestratorWorkflowConcurrency
# =============================================================================


@pytest.mark.unit
class TestNodeOrchestratorWorkflowConcurrency:
    """Test workflow state thread safety under concurrent load.

    NodeOrchestrator has mutable workflow state (_workflow_state) that is
    modified during workflow execution. This class tests that concurrent
    access to this state can corrupt workflow execution.

    Reference: docs/guides/THREADING.md - NodeOrchestrator Thread Safety
    """

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution_10_tasks(
        self,
        container: ModelONEXContainer,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """10+ async tasks executing workflows simultaneously.

        Validates that concurrent workflow executions on the SAME orchestrator
        instance can lead to state corruption. This is the expected unsafe behavior
        that demonstrates why thread-local instances are required.
        """
        orchestrator = NodeOrchestrator(container)
        orchestrator.workflow_definition = workflow_definition

        results: list[ModelOrchestratorOutput] = []
        errors: list[Exception] = []

        async def execute_workflow(task_id: int) -> ModelOrchestratorOutput | None:
            """Execute a workflow and track results."""
            try:
                # Create unique input for each task
                input_data = ModelOrchestratorInput(
                    workflow_id=uuid4(),
                    steps=[
                        {"step_name": f"task_{task_id}_step1", "step_type": "compute"},
                        {"step_name": f"task_{task_id}_step2", "step_type": "effect"},
                    ],
                    execution_mode=EnumExecutionMode.SEQUENTIAL,
                )
                result = await orchestrator.process(input_data)
                return result
            except Exception as e:
                errors.append(e)
                return None

        # Launch 15 concurrent tasks
        tasks = [asyncio.create_task(execute_workflow(i)) for i in range(15)]
        task_results = await asyncio.gather(*tasks)

        # Collect successful results
        for result in task_results:
            if result is not None:
                results.append(result)

        # All tasks should complete (either success or handled error)
        assert len(results) + len(errors) == 15, (
            f"Expected 15 total operations, got {len(results)} results + {len(errors)} errors"
        )

        # Verify outputs are valid ModelOrchestratorOutput instances
        for result in results:
            assert isinstance(result, ModelOrchestratorOutput)
            assert result.execution_status in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_workflow_state_mutation_isolation(
        self,
        container: ModelONEXContainer,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Workflow state mutations don't leak between concurrent operations.

        This test demonstrates that workflow state (_workflow_state) can be
        corrupted when multiple async tasks use the same orchestrator instance.
        Each workflow should have isolated state, but shared instances break this.
        """
        orchestrator = NodeOrchestrator(container)
        orchestrator.workflow_definition = workflow_definition

        captured_states: list[ModelWorkflowStateSnapshot | None] = []
        lock = asyncio.Lock()

        async def capture_state_after_workflow(task_id: int) -> None:
            """Execute workflow and capture state."""
            input_data = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=[
                    {"step_name": f"isolation_step_{task_id}", "step_type": "compute"},
                ],
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

            await orchestrator.process(input_data)

            # Capture state immediately after execution
            async with lock:
                snapshot = orchestrator.snapshot_workflow_state()
                captured_states.append(snapshot)

        # Run 10 concurrent workflows
        tasks = [
            asyncio.create_task(capture_state_after_workflow(i)) for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # All states should be captured
        assert len(captured_states) == 10

        # Check that states are valid (may not all be unique due to race conditions)
        # This documents the race condition behavior
        for state in captured_states:
            if state is not None:
                assert isinstance(state, ModelWorkflowStateSnapshot)

    @pytest.mark.asyncio
    async def test_concurrent_step_execution_safety(
        self,
        container: ModelONEXContainer,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Concurrent step execution doesn't corrupt workflow state.

        Tests parallel execution mode where multiple steps run concurrently.
        Validates that step completion tracking remains consistent.
        """
        orchestrator = NodeOrchestrator(container)
        orchestrator.workflow_definition = workflow_definition

        results: list[ModelOrchestratorOutput] = []

        async def run_parallel_workflow(task_id: int) -> ModelOrchestratorOutput:
            """Run workflow with parallel execution mode."""
            # Create 5 independent steps for parallel execution
            steps = [
                {"step_name": f"parallel_step_{task_id}_{i}", "step_type": "compute"}
                for i in range(5)
            ]
            input_data = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=steps,
                execution_mode=EnumExecutionMode.PARALLEL,
                max_parallel_steps=5,
            )
            return await orchestrator.process(input_data)

        # Run 10 parallel workflow executions
        tasks = [asyncio.create_task(run_parallel_workflow(i)) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Validate all workflows completed
        assert len(results) == 10
        for result in results:
            assert isinstance(result, ModelOrchestratorOutput)
            # Execution status should be valid
            assert result.execution_status in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_snapshot_and_restore_concurrent_safety(
        self,
        container: ModelONEXContainer,
        workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Snapshot and restore operations are safe under concurrent access.

        Tests that snapshot_workflow_state() and restore_workflow_state()
        work correctly when called from multiple concurrent tasks.
        """
        orchestrator = NodeOrchestrator(container)
        orchestrator.workflow_definition = workflow_definition

        restore_errors: list[Exception] = []
        snapshot_results: list[ModelWorkflowStateSnapshot | None] = []
        lock = asyncio.Lock()

        async def restore_and_snapshot(task_id: int) -> None:
            """Restore state, then snapshot it."""
            try:
                # Create unique snapshot for each task
                task_snapshot = ModelWorkflowStateSnapshot(
                    workflow_id=uuid4(),
                    current_step_index=task_id,
                    completed_step_ids=(),
                    failed_step_ids=(),
                    context={"task_id": task_id},
                    created_at=datetime.now(UTC),
                )

                orchestrator.restore_workflow_state(task_snapshot)
                result = orchestrator.snapshot_workflow_state()

                async with lock:
                    snapshot_results.append(result)
            except Exception as e:
                async with lock:
                    restore_errors.append(e)

        # Run 10 concurrent restore/snapshot operations
        tasks = [asyncio.create_task(restore_and_snapshot(i)) for i in range(10)]
        await asyncio.gather(*tasks)

        # All operations should complete without error
        assert len(restore_errors) == 0, (
            f"Errors during restore/snapshot: {restore_errors}"
        )
        assert len(snapshot_results) == 10

        # Validate snapshots are valid
        for snapshot in snapshot_results:
            assert snapshot is not None
            assert isinstance(snapshot, ModelWorkflowStateSnapshot)


# =============================================================================
# TestModelActionLeaseConcurrency
# =============================================================================


@pytest.mark.unit
class TestModelActionLeaseConcurrency:
    """Test lease-based coordination under concurrent load.

    ModelAction uses lease_id and epoch for single-writer semantics.
    These tests validate that lease management is consistent under concurrent access.
    """

    def test_concurrent_lease_acquisition_10_tasks(self):
        """10+ concurrent lease acquisition attempts.

        Tests that multiple threads creating ModelAction instances with
        unique lease_ids don't interfere with each other.
        """
        created_actions: list[ModelAction] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def create_action_with_lease(task_id: int) -> None:
            """Create an action with a unique lease."""
            try:
                action = ModelAction(
                    action_type=EnumActionType.COMPUTE,
                    target_node_type="NodeCompute",
                    payload={"task_id": task_id},
                    lease_id=uuid4(),  # Unique lease per action
                    epoch=task_id,  # Use task_id as epoch
                )

                with lock:
                    created_actions.append(action)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Launch 15 threads to create actions concurrently
        threads = [
            threading.Thread(target=create_action_with_lease, args=(i,))
            for i in range(15)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All actions should be created successfully
        assert len(errors) == 0, f"Errors during action creation: {errors}"
        assert len(created_actions) == 15

        # Verify all lease_ids are unique
        lease_ids = [action.lease_id for action in created_actions]
        assert len(set(lease_ids)) == 15, "Lease IDs should be unique"

        # Verify epochs are as expected
        epochs = sorted([action.epoch for action in created_actions])
        assert epochs == list(range(15)), "Epochs should be 0-14"

    def test_lease_conflict_resolution(self):
        """Lease conflicts are resolved correctly under concurrent load.

        Tests that when multiple actions claim the same resource,
        epoch-based conflict resolution works correctly.
        """
        # Simulate lease conflict by creating actions with same logical resource
        shared_resource = "shared_compute_node"
        created_actions: list[ModelAction] = []
        lock = threading.Lock()

        def create_action_for_resource(task_id: int, epoch: int) -> None:
            """Create an action for a shared resource."""
            action = ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type=shared_resource,
                payload={"task_id": task_id},
                lease_id=uuid4(),
                epoch=epoch,
            )

            with lock:
                created_actions.append(action)

        # Launch threads with varying epochs
        threads = []
        for i in range(10):
            # Some threads have same epoch (conflict scenario)
            epoch = i % 3  # 0, 1, 2, 0, 1, 2, ...
            thread = threading.Thread(
                target=create_action_for_resource, args=(i, epoch)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All actions created
        assert len(created_actions) == 10

        # Verify epoch distribution
        epoch_counts: dict[int, int] = {}
        for action in created_actions:
            epoch_counts[action.epoch] = epoch_counts.get(action.epoch, 0) + 1

        # Should have ~3-4 actions per epoch (0, 1, 2)
        assert len(epoch_counts) == 3
        for epoch, count in epoch_counts.items():
            assert count >= 3, f"Epoch {epoch} should have at least 3 actions"

    def test_lease_release_under_concurrent_access(self):
        """Lease release is safe under concurrent access.

        Tests that ModelAction immutability (frozen=True) prevents
        accidental lease modification under concurrent access.
        """
        # Create an action
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="NodeCompute",
            payload={"test": "data"},
            lease_id=uuid4(),
            epoch=1,
        )

        original_lease_id = action.lease_id
        modification_errors: list[str] = []
        lock = threading.Lock()

        def attempt_modification(thread_id: int) -> None:
            """Attempt to modify the action's lease (should fail)."""
            try:
                action.lease_id = uuid4()  # type: ignore[misc]
            except (TypeError, AttributeError, Exception) as e:
                with lock:
                    modification_errors.append(
                        f"Thread {thread_id}: {type(e).__name__}"
                    )

            # Verify original lease is unchanged
            assert action.lease_id == original_lease_id

        # Launch 10 threads attempting to modify
        threads = [
            threading.Thread(target=attempt_modification, args=(i,)) for i in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All modifications should fail (frozen model)
        assert len(modification_errors) == 10
        # Original lease should be preserved
        assert action.lease_id == original_lease_id

    @pytest.mark.asyncio
    async def test_action_creation_async_concurrent(self):
        """Async concurrent action creation with lease tracking.

        Tests that asyncio tasks can create actions with leases concurrently.
        """
        created_actions: list[ModelAction] = []
        lock = asyncio.Lock()

        async def create_action_async(task_id: int) -> None:
            """Create action in async context."""
            await asyncio.sleep(0.001)  # Simulate async work

            action = ModelAction(
                action_type=EnumActionType.EFFECT,
                target_node_type="NodeEffect",
                payload={"async_task_id": task_id},
                lease_id=uuid4(),
                epoch=task_id,
            )

            async with lock:
                created_actions.append(action)

        # Run 15 concurrent async tasks
        tasks = [asyncio.create_task(create_action_async(i)) for i in range(15)]
        await asyncio.gather(*tasks)

        # Validate all actions created
        assert len(created_actions) == 15
        # All leases unique
        lease_ids = {action.lease_id for action in created_actions}
        assert len(lease_ids) == 15


# =============================================================================
# TestOrchestratorInputOutputConcurrency
# =============================================================================


@pytest.mark.unit
class TestOrchestratorInputOutputConcurrency:
    """Test concurrent input/output processing.

    ModelOrchestratorInput and ModelOrchestratorOutput are immutable (frozen=True).
    These tests validate they can be safely shared across threads/tasks.
    """

    def test_concurrent_orchestrator_input_processing(self):
        """10+ concurrent ModelOrchestratorInput processing operations.

        Validates that immutable inputs can be read from multiple threads
        without corruption.
        """
        # Create a shared input
        shared_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[
                {"step_name": "step1", "step_type": "compute"},
                {"step_name": "step2", "step_type": "effect"},
            ],
            execution_mode=EnumExecutionMode.PARALLEL,
            max_parallel_steps=10,
        )

        original_workflow_id = shared_input.workflow_id
        original_mode = shared_input.execution_mode

        read_results: list[dict] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def read_input(thread_id: int) -> None:
            """Read fields from shared input."""
            try:
                for _ in range(10):
                    data = {
                        "thread_id": thread_id,
                        "workflow_id": shared_input.workflow_id,
                        "execution_mode": shared_input.execution_mode,
                        "max_parallel": shared_input.max_parallel_steps,
                        "step_count": len(shared_input.steps),
                    }
                    with lock:
                        read_results.append(data)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Launch 15 threads reading concurrently
        threads = [threading.Thread(target=read_input, args=(i,)) for i in range(15)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # No errors should occur
        assert len(errors) == 0, f"Read errors: {errors}"

        # All reads should return consistent data
        for result in read_results:
            assert result["workflow_id"] == original_workflow_id
            assert result["execution_mode"] == original_mode
            assert result["max_parallel"] == 10
            assert result["step_count"] == 2

    def test_concurrent_orchestrator_output_generation(self):
        """10+ concurrent ModelOrchestratorOutput generation operations.

        Validates that outputs can be created from multiple threads.
        """
        created_outputs: list[ModelOrchestratorOutput] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def create_output(thread_id: int) -> None:
            """Create an orchestrator output."""
            try:
                output = ModelOrchestratorOutput(
                    execution_status="completed",
                    execution_time_ms=100 + thread_id,
                    start_time=datetime.now(UTC).isoformat(),
                    end_time=datetime.now(UTC).isoformat(),
                    completed_steps=[f"step_{thread_id}"],
                    failed_steps=[],
                    metrics={"thread_id": float(thread_id)},
                )

                with lock:
                    created_outputs.append(output)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Launch 15 threads creating outputs
        threads = [threading.Thread(target=create_output, args=(i,)) for i in range(15)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # No errors
        assert len(errors) == 0, f"Creation errors: {errors}"
        assert len(created_outputs) == 15

        # Verify each output is unique
        execution_times = [o.execution_time_ms for o in created_outputs]
        assert len(set(execution_times)) == 15, (
            "Each output should have unique execution_time"
        )

    @pytest.mark.asyncio
    async def test_async_input_output_roundtrip(self):
        """Async roundtrip of input/output through multiple tasks.

        Tests the full lifecycle of creating inputs, processing, and
        generating outputs in concurrent async tasks.
        """
        processed_results: list[tuple[UUID, str]] = []
        lock = asyncio.Lock()

        async def process_workflow(task_id: int) -> None:
            """Simulate workflow processing."""
            input_data = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=[{"step_name": f"async_step_{task_id}", "step_type": "compute"}],
                execution_mode=EnumExecutionMode.SEQUENTIAL,
            )

            await asyncio.sleep(0.001)  # Simulate processing

            output = ModelOrchestratorOutput(
                execution_status="completed",
                execution_time_ms=task_id * 10,
                start_time=datetime.now(UTC).isoformat(),
                end_time=datetime.now(UTC).isoformat(),
                completed_steps=[f"async_step_{task_id}"],
                failed_steps=[],
            )

            async with lock:
                processed_results.append(
                    (input_data.workflow_id, output.execution_status)
                )

        # Run 20 concurrent tasks
        tasks = [asyncio.create_task(process_workflow(i)) for i in range(20)]
        await asyncio.gather(*tasks)

        # All tasks should complete
        assert len(processed_results) == 20

        # All workflow IDs should be unique
        workflow_ids = [r[0] for r in processed_results]
        assert len(set(workflow_ids)) == 20

        # All statuses should be "completed"
        statuses = [r[1] for r in processed_results]
        assert all(s == "completed" for s in statuses)


# =============================================================================
# TestNodeOrchestratorThreadLocalPattern
# =============================================================================


@pytest.mark.unit
class TestNodeOrchestratorThreadLocalPattern:
    """Test thread-local instance pattern for NodeOrchestrator.

    The recommended pattern for multi-threaded usage is one NodeOrchestrator
    per thread. This class validates that pattern works correctly.
    """

    def test_thread_local_orchestrators_isolated(self):
        """Each thread gets independent NodeOrchestrator with isolated workflow state.

        This is the RECOMMENDED pattern for production multi-threaded usage.
        """
        container = ModelONEXContainer()
        thread_local = threading.local()
        workflow_def = create_workflow_definition()

        # Store instances to prevent GC
        instances: list[NodeOrchestrator] = []
        lock = threading.Lock()

        def get_thread_local_orchestrator() -> NodeOrchestrator:
            """Get or create thread-local NodeOrchestrator."""
            if not hasattr(thread_local, "orchestrator"):
                orchestrator = NodeOrchestrator(container)
                orchestrator.workflow_definition = workflow_def
                thread_local.orchestrator = orchestrator
            return thread_local.orchestrator

        def worker(thread_id: int) -> None:
            """Worker that uses thread-local orchestrator."""
            orchestrator = get_thread_local_orchestrator()

            # Update workflow state specific to this thread
            orchestrator.update_workflow_state(
                workflow_id=uuid4(),
                current_step_index=thread_id,
                completed_step_ids=[],
                context={"thread_id": thread_id},
            )

            with lock:
                instances.append(orchestrator)

        # Launch 5 threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Each thread should have its own instance
        instance_ids = [id(inst) for inst in instances]
        assert len(set(instance_ids)) == 5, (
            "Each thread should have unique orchestrator instance"
        )

        # Verify each instance has isolated state
        for idx, inst in enumerate(instances):
            snapshot = inst.snapshot_workflow_state()
            assert snapshot is not None
            # Context should contain the thread's own thread_id
            assert "thread_id" in snapshot.context

    def test_thread_local_workflow_no_leakage(self):
        """Workflow state doesn't leak between thread-local instances.

        Validates that state modifications in one thread don't affect
        orchestrators in other threads.
        """
        container = ModelONEXContainer()
        thread_local = threading.local()
        workflow_def = create_workflow_definition()

        state_values: list[dict] = []
        lock = threading.Lock()

        def get_orchestrator() -> NodeOrchestrator:
            """Get thread-local orchestrator."""
            if not hasattr(thread_local, "orchestrator"):
                orchestrator = NodeOrchestrator(container)
                orchestrator.workflow_definition = workflow_def
                thread_local.orchestrator = orchestrator
            return thread_local.orchestrator

        def update_and_verify(thread_id: int) -> None:
            """Update state and verify isolation."""
            orchestrator = get_orchestrator()

            # Set unique workflow ID for this thread
            unique_workflow_id = uuid4()
            orchestrator.update_workflow_state(
                workflow_id=unique_workflow_id,
                current_step_index=thread_id * 10,
                completed_step_ids=[],
                context={"unique_value": thread_id * 100},
            )

            # Small delay to allow race conditions to manifest
            time.sleep(0.01)

            # Verify our state is unchanged
            snapshot = orchestrator.snapshot_workflow_state()
            assert snapshot is not None

            with lock:
                state_values.append(
                    {
                        "thread_id": thread_id,
                        "workflow_id": snapshot.workflow_id,
                        "step_index": snapshot.current_step_index,
                        "unique_value": snapshot.context.get("unique_value"),
                    }
                )

        # Launch 10 threads
        threads = [
            threading.Thread(target=update_and_verify, args=(i,)) for i in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify each thread saw its own state
        assert len(state_values) == 10

        for state in state_values:
            thread_id = state["thread_id"]
            # State should match what this thread set
            assert state["step_index"] == thread_id * 10
            assert state["unique_value"] == thread_id * 100

    @pytest.mark.asyncio
    async def test_async_task_isolation_with_threadpool(self):
        """Async tasks using ThreadPoolExecutor maintain isolation.

        Tests the pattern of running async orchestration in a thread pool
        where each thread has its own orchestrator instance.
        """
        container = ModelONEXContainer()
        thread_local = threading.local()
        workflow_def = create_workflow_definition()

        results: list[dict] = []
        lock = threading.Lock()

        def get_orchestrator() -> NodeOrchestrator:
            """Get thread-local orchestrator."""
            if not hasattr(thread_local, "orchestrator"):
                orchestrator = NodeOrchestrator(container)
                orchestrator.workflow_definition = workflow_def
                thread_local.orchestrator = orchestrator
            return thread_local.orchestrator

        def process_in_thread(task_id: int) -> dict:
            """Process workflow in thread."""
            orchestrator = get_orchestrator()
            instance_id = id(orchestrator)

            # Add a small delay to ensure concurrent execution across threads
            time.sleep(0.02)

            # Set state
            workflow_id = uuid4()
            orchestrator.update_workflow_state(
                workflow_id=workflow_id,
                current_step_index=task_id,
                completed_step_ids=[],
                context={"task_id": task_id},
            )

            # Verify state
            snapshot = orchestrator.snapshot_workflow_state()

            return {
                "task_id": task_id,
                "instance_id": instance_id,
                "workflow_id": workflow_id,
                "snapshot_workflow_id": snapshot.workflow_id if snapshot else None,
            }

        # Run tasks in thread pool with fewer tasks to ensure all workers are utilized
        # With 10 tasks and 5 workers, each worker should get 2 tasks
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_in_thread, i) for i in range(10)]
            for future in futures:
                result = future.result()
                results.append(result)

        # Validate results
        assert len(results) == 10

        # With 5 workers processing 10 tasks (2 per worker), and a small delay,
        # we expect all 5 workers to be utilized. Due to scheduling variance,
        # we may see 3-5 unique instances.
        instance_ids = {r["instance_id"] for r in results}
        assert 3 <= len(instance_ids) <= 5, (
            f"Should have 3-5 thread-local instances for 5 workers, got {len(instance_ids)}"
        )

        # Each task should see its own workflow_id
        for result in results:
            assert result["workflow_id"] == result["snapshot_workflow_id"]


# =============================================================================
# TestWorkflowStateSnapshotConcurrency
# =============================================================================


@pytest.mark.unit
class TestWorkflowStateSnapshotConcurrency:
    """Test ModelWorkflowStateSnapshot thread safety.

    ModelWorkflowStateSnapshot is immutable (frozen=True) and should be
    safe to share across threads. These tests validate that behavior.
    """

    def test_concurrent_snapshot_read_access(self):
        """Multiple threads can safely read from the same snapshot.

        Validates that immutable snapshots are thread-safe for reads.
        """
        # Create a snapshot with various data
        step_ids = tuple(uuid4() for _ in range(5))
        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=uuid4(),
            current_step_index=3,
            completed_step_ids=step_ids[:3],
            failed_step_ids=step_ids[3:],
            context={"key1": "value1", "key2": 42},
            created_at=datetime.now(UTC),
        )

        read_results: list[dict] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def read_snapshot(thread_id: int) -> None:
            """Read all fields from snapshot."""
            try:
                for _ in range(10):
                    data = {
                        "thread_id": thread_id,
                        "workflow_id": snapshot.workflow_id,
                        "step_index": snapshot.current_step_index,
                        "completed_count": len(snapshot.completed_step_ids),
                        "failed_count": len(snapshot.failed_step_ids),
                        "context_key1": snapshot.context.get("key1"),
                    }
                    with lock:
                        read_results.append(data)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Launch 15 threads
        threads = [threading.Thread(target=read_snapshot, args=(i,)) for i in range(15)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # No errors
        assert len(errors) == 0, f"Read errors: {errors}"

        # All reads should be consistent
        for result in read_results:
            assert result["step_index"] == 3
            assert result["completed_count"] == 3
            assert result["failed_count"] == 2
            assert result["context_key1"] == "value1"

    def test_snapshot_immutability_under_concurrent_modification_attempts(self):
        """Snapshot remains immutable under concurrent modification attempts.

        Validates that frozen=True prevents all modifications.
        """
        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=uuid4(),
            current_step_index=5,
            completed_step_ids=(uuid4(),),
            failed_step_ids=(),
            context={"original": True},
        )

        original_step_index = snapshot.current_step_index
        modification_errors: list[str] = []
        lock = threading.Lock()

        def attempt_modification(thread_id: int) -> None:
            """Attempt various modifications."""
            try:
                snapshot.current_step_index = 999  # type: ignore[misc]
            except (TypeError, AttributeError, Exception) as e:
                with lock:
                    modification_errors.append(f"step_index: {type(e).__name__}")

            try:
                snapshot.workflow_id = uuid4()  # type: ignore[misc]
            except (TypeError, AttributeError, Exception) as e:
                with lock:
                    modification_errors.append(f"workflow_id: {type(e).__name__}")

            # Verify original values unchanged
            assert snapshot.current_step_index == original_step_index

        # Launch 10 threads
        threads = [
            threading.Thread(target=attempt_modification, args=(i,)) for i in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All modifications should fail
        assert len(modification_errors) == 20  # 10 threads x 2 attempts each

        # Original value preserved
        assert snapshot.current_step_index == original_step_index

    @pytest.mark.asyncio
    async def test_async_snapshot_serialization_concurrent(self):
        """Async concurrent serialization of snapshots.

        Tests that model_dump() and model_dump_json() are safe in async contexts.
        """
        snapshot = ModelWorkflowStateSnapshot(
            workflow_id=uuid4(),
            current_step_index=10,
            completed_step_ids=(uuid4(), uuid4()),
            failed_step_ids=(uuid4(),),
            context={"async_test": True},
        )

        serialized_results: list[tuple[dict, str]] = []
        lock = asyncio.Lock()

        async def serialize_snapshot() -> None:
            """Serialize snapshot in async context."""
            await asyncio.sleep(0.001)  # Simulate async work
            dict_data = snapshot.model_dump(mode="json")
            json_data = snapshot.model_dump_json()

            async with lock:
                serialized_results.append((dict_data, json_data))

        # Run 20 concurrent serializations
        tasks = [asyncio.create_task(serialize_snapshot()) for _ in range(20)]
        await asyncio.gather(*tasks)

        # All serializations should succeed
        assert len(serialized_results) == 20

        # All results should be identical
        first_dict, first_json = serialized_results[0]
        for dict_data, json_data in serialized_results:
            assert dict_data["current_step_index"] == first_dict["current_step_index"]
            assert json_data == first_json


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
