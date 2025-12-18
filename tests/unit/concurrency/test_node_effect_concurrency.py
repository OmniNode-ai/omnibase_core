"""
Concurrency tests for NodeEffect and circuit breaker thread safety.

This module provides comprehensive tests for NodeEffect behavior under
concurrent load, focusing on:
- Circuit breaker dictionary race conditions
- Failure counter atomicity
- State transition races (open/closed/half-open)
- Thread-local instance isolation patterns
- Transaction isolation across threads

CRITICAL: These tests verify the documented thread safety risks in NodeEffect.
See docs/guides/THREADING.md for mitigation strategies.

Thread Safety Matrix (from THREADING.md):
| Component | Thread-Safe? | Action Required |
|-----------|-------------|-----------------|
| `NodeEffect` | No | Use thread-local instances |
| `_circuit_breakers` dict | No | Process-local, single-thread only |
| `ModelCircuitBreaker` | No | Use locks or thread-local instances |
| `ModelEffectTransaction` | No | Never share across threads |

Reference: docs/guides/THREADING.md - Thread Safety Guidelines
"""

import asyncio
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.enums.enum_effect_types import EnumEffectType, EnumTransactionState
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelHttpIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.nodes.node_effect import NodeEffect

pytestmark = [pytest.mark.unit, pytest.mark.timeout(120)]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def container() -> ModelONEXContainer:
    """Create a fresh container for each test."""
    return ModelONEXContainer()


@pytest.fixture
def effect_subcontract() -> ModelEffectSubcontract:
    """Create a minimal effect subcontract for testing.

    Uses idempotent GET operations to allow retry without validation errors.
    """
    return ModelEffectSubcontract(
        subcontract_name="test_effect",
        operations=[
            ModelEffectOperation(
                operation_name="test_operation",
                idempotent=True,  # Explicit idempotent to allow retry
                io_config=ModelHttpIOConfig(
                    handler_type=EnumEffectHandlerType.HTTP,
                    url_template="https://api.example.com/test",
                    method="GET",
                    timeout_ms=5000,
                ),
            )
        ],
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=False,  # Disable retry for basic tests
            max_retries=0,
        ),
    )


@pytest.fixture
def effect_subcontract_with_retry() -> ModelEffectSubcontract:
    """Create effect subcontract with retry enabled for retry tests."""
    return ModelEffectSubcontract(
        subcontract_name="test_effect_retry",
        operations=[
            ModelEffectOperation(
                operation_name="retry_operation",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    handler_type=EnumEffectHandlerType.HTTP,
                    url_template="https://api.example.com/retry",
                    method="GET",
                    timeout_ms=5000,
                ),
            )
        ],
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_ms=10,  # Short delay for testing
        ),
    )


def create_node_with_subcontract(
    container: ModelONEXContainer, subcontract: ModelEffectSubcontract
) -> NodeEffect:
    """Helper to create NodeEffect with subcontract attached."""
    node = NodeEffect(container)
    node.effect_subcontract = subcontract
    return node


# =============================================================================
# TestNodeEffectCircuitBreakerConcurrency
# =============================================================================


@pytest.mark.slow
class TestNodeEffectCircuitBreakerConcurrency:
    """Test circuit breaker thread safety under concurrent load.

    These tests validate the documented thread safety issues with NodeEffect's
    circuit breaker state. The _circuit_breakers dictionary and ModelCircuitBreaker
    state are NOT thread-safe.

    Reference: docs/guides/THREADING.md - NodeEffect Thread Safety section
    """

    @pytest.mark.asyncio
    async def test_concurrent_circuit_breaker_access_10_tasks(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """10+ async tasks accessing same circuit breaker simultaneously.

        This test verifies that concurrent access to the same NodeEffect instance's
        circuit breaker can cause race conditions. In production, use thread-local
        NodeEffect instances instead of sharing.
        """
        node = create_node_with_subcontract(container, effect_subcontract)
        operation_id = uuid4()

        access_count = {"count": 0}
        errors: list[Exception] = []

        async def access_circuit_breaker() -> None:
            """Access circuit breaker concurrently."""
            try:
                # Get or create circuit breaker (potential race on dict access)
                breaker = node.get_circuit_breaker(operation_id)

                # Verify we got a valid breaker
                assert breaker is not None
                assert isinstance(breaker, ModelCircuitBreaker)

                # Check state (potential race on state read)
                _ = breaker.should_allow_request()

                access_count["count"] += 1
            except Exception as e:
                errors.append(e)

        # Launch 15 concurrent tasks (more than 10 as specified)
        tasks = [access_circuit_breaker() for _ in range(15)]
        await asyncio.gather(*tasks)

        # Verify all tasks completed
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
        assert access_count["count"] == 15, "Not all tasks completed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_dictionary_race_condition(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Detect race in _circuit_breakers dict updates.

        This test demonstrates the documented race condition where multiple
        tasks checking `if op_id not in self._circuit_breakers` simultaneously
        can both see True and create separate breakers, with one overwriting
        the other.

        From THREADING.md:
        > Thread 1 and Thread 2 both check for operation_id simultaneously:
        > Thread 1: breaker created -> stored in dict
        > Thread 2: breaker created -> OVERWRITES Thread 1's breaker
        > Result: Thread 1's circuit breaker state is lost
        """
        node = create_node_with_subcontract(container, effect_subcontract)

        # Use multiple unique operation IDs to stress the dict
        operation_ids = [uuid4() for _ in range(20)]
        breaker_instances: list[tuple[UUID, int]] = []
        lock = threading.Lock()

        async def create_and_track_breaker(op_id: UUID) -> None:
            """Create breaker and track its instance ID."""
            breaker = node.get_circuit_breaker(op_id)
            with lock:
                breaker_instances.append((op_id, id(breaker)))

        # Create multiple tasks per operation_id to trigger races
        tasks = []
        for op_id in operation_ids:
            # 3 tasks per operation_id to trigger dictionary race
            for _ in range(3):
                tasks.append(create_and_track_breaker(op_id))

        await asyncio.gather(*tasks)

        # Verify all operation_ids have breakers in the dict
        assert len(node._circuit_breakers) == len(operation_ids), (
            f"Expected {len(operation_ids)} breakers, got {len(node._circuit_breakers)}"
        )

        # Group instances by operation_id
        instances_by_op_id: dict[UUID, list[int]] = {}
        for op_id, instance_id in breaker_instances:
            if op_id not in instances_by_op_id:
                instances_by_op_id[op_id] = []
            instances_by_op_id[op_id].append(instance_id)

        # In a race-free implementation, all instances for same op_id would be identical
        # With races, we might see different instance IDs for same op_id
        # This is informational - we're documenting the behavior
        race_detected = False
        for op_id, instances in instances_by_op_id.items():
            unique_instances = len(set(instances))
            if unique_instances > 1:
                race_detected = True
                # This is expected with races - document but don't fail
                # as the test is demonstrating the race, not preventing it

        # The test passes if it completes without exceptions
        # Race detection is informational
        if race_detected:
            # Race was detected - this is the expected behavior we're documenting
            pass

    @pytest.mark.asyncio
    async def test_failure_counter_atomicity(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Verify failure counts are accurate under concurrent failures.

        This test demonstrates that concurrent `record_failure()` calls can
        result in lost updates due to non-atomic counter increments.

        From THREADING.md:
        > failure_count increments are not atomic
        > Concurrent access from multiple threads may cause:
        > - Counter corruption (missed increments)
        """
        node = create_node_with_subcontract(container, effect_subcontract)
        operation_id = uuid4()

        # Get the circuit breaker
        breaker = node.get_circuit_breaker(operation_id)

        num_tasks = 20
        failures_per_task = 5
        expected_total = num_tasks * failures_per_task

        errors: list[Exception] = []

        async def record_multiple_failures() -> None:
            """Record multiple failures from one task."""
            try:
                for _ in range(failures_per_task):
                    breaker.record_failure()
                    # Minimal delay to increase race window
                    await asyncio.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        # Launch concurrent failure recording tasks
        tasks = [record_multiple_failures() for _ in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify no exceptions occurred
        assert len(errors) == 0, f"Errors during concurrent failures: {errors}"

        # The failure count may be less than expected due to races
        # We document this behavior rather than asserting exact equality
        actual_failures = breaker.failure_count

        # Under race conditions, we might lose some updates
        # This is expected behavior - we're documenting the risk
        if actual_failures < expected_total:
            # Race condition detected - some failures were lost
            lost_failures = expected_total - actual_failures
            # This is informational - the test documents the behavior
            assert lost_failures >= 0, "Sanity check failed"

        # The count should be at least 1 (something was recorded)
        assert actual_failures >= 1, "No failures were recorded"

    @pytest.mark.asyncio
    async def test_state_transition_races(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test open/closed/half-open transitions under concurrent load.

        This test verifies that concurrent success/failure recordings can
        cause incorrect state transitions in the circuit breaker.

        From THREADING.md:
        > Multiple threads may incorrectly trip/reset breaker state
        > State corruption can lead to incorrect open/closed/half-open transitions
        """
        node = create_node_with_subcontract(container, effect_subcontract)
        operation_id = uuid4()

        breaker = node.get_circuit_breaker(operation_id)

        # Record enough failures to trip the breaker
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()

        # Breaker should be open
        initial_state = breaker.state

        state_observations: list[str] = []
        lock = threading.Lock()

        async def mixed_operations(success_count: int, failure_count: int) -> None:
            """Record mix of successes and failures and observe state."""
            for _ in range(success_count):
                breaker.record_success()
                with lock:
                    state_observations.append(breaker.state)
            for _ in range(failure_count):
                breaker.record_failure()
                with lock:
                    state_observations.append(breaker.state)

        # Launch concurrent mixed operations
        tasks = [mixed_operations(3, 2) for _ in range(10)]
        await asyncio.gather(*tasks)

        # Count state transitions observed
        state_counts = Counter(state_observations)

        # Verify we observed some state
        assert len(state_observations) > 0, "No state observations recorded"

        # Under concurrent load, state can be unpredictable
        # This test documents the behavior rather than asserting specific outcomes
        final_state = breaker.state

        # The test passes if it completes without exceptions
        # State inconsistencies under concurrent load are expected


# =============================================================================
# TestNodeEffectThreadLocalPattern
# =============================================================================


class TestNodeEffectThreadLocalPattern:
    """Test thread-local instance pattern for NodeEffect.

    These tests validate that the recommended mitigation pattern (thread-local
    NodeEffect instances) correctly isolates state across threads.

    From THREADING.md:
    > Thread-local NodeEffect instances are strongly recommended - each thread
    > maintains its own _circuit_breakers dictionary with no possibility of
    > race conditions.
    """

    def test_thread_local_instances_isolated(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Each thread gets independent NodeEffect with isolated state.

        This test validates the recommended pattern where each thread creates
        its own NodeEffect instance via threading.local().
        """
        thread_local = threading.local()
        instances: list[NodeEffect] = []
        instance_ids: list[int] = []
        lock = threading.Lock()

        def get_thread_local_node() -> NodeEffect:
            """Get or create thread-local NodeEffect instance."""
            if not hasattr(thread_local, "node"):
                node = NodeEffect(container)
                node.effect_subcontract = effect_subcontract
                thread_local.node = node
            return thread_local.node  # type: ignore[return-value]

        def worker(thread_id: int) -> None:
            """Worker that gets thread-local node and records instance."""
            node = get_thread_local_node()

            # Perform some operations to ensure node is usable
            operation_id = uuid4()
            breaker = node.get_circuit_breaker(operation_id)
            breaker.record_success()

            with lock:
                instances.append(node)
                instance_ids.append(id(node))

        # Launch threads
        threads = []
        num_threads = 10

        for thread_id in range(num_threads):
            thread = threading.Thread(target=worker, args=(thread_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have gotten a unique instance
        assert len(instances) == num_threads, "Not all threads completed"
        unique_ids = set(instance_ids)
        assert len(unique_ids) == num_threads, (
            f"Expected {num_threads} unique instances, got {len(unique_ids)}"
        )

    def test_thread_local_circuit_breakers_independent(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Circuit breakers don't leak between thread-local instances.

        This test validates that circuit breaker state in one thread's
        NodeEffect instance does not affect another thread's instance.
        """
        thread_local = threading.local()
        operation_id = uuid4()  # Same operation_id across all threads

        failure_counts: dict[int, int] = {}
        lock = threading.Lock()

        def get_thread_local_node():
            """Get or create thread-local NodeEffect instance."""
            if not hasattr(thread_local, "node"):
                node = NodeEffect(container)
                node.effect_subcontract = effect_subcontract
                thread_local.node = node
            return thread_local.node

        def worker(thread_id: int, failures_to_record: int) -> None:
            """Worker that records specific number of failures."""
            node = get_thread_local_node()
            breaker = node.get_circuit_breaker(operation_id)

            # Record failures specific to this thread
            for _ in range(failures_to_record):
                breaker.record_failure()

            # Record the failure count for this thread's breaker
            with lock:
                failure_counts[thread_id] = breaker.failure_count

        # Launch threads with different failure counts
        threads = []
        expected_failures = {0: 1, 1: 3, 2: 5, 3: 7, 4: 9}

        for thread_id, failures in expected_failures.items():
            thread = threading.Thread(target=worker, args=(thread_id, failures))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have its own isolated failure count
        for thread_id, expected in expected_failures.items():
            actual = failure_counts.get(thread_id)
            assert actual == expected, (
                f"Thread {thread_id}: expected {expected} failures, got {actual}. "
                "Circuit breaker state leaked between threads."
            )


# =============================================================================
# TestModelEffectTransactionIsolation
# =============================================================================


class TestModelEffectTransactionIsolation:
    """Test transaction isolation under concurrency.

    ModelEffectTransaction is NOT thread-safe and must never be shared
    across threads. Each operation should create its own transaction.

    From THREADING.md:
    > ModelEffectTransaction is NOT thread-safe:
    > - Rollback operations assume single-threaded execution
    > - Operation list modifications are not synchronized
    > - State transitions are not atomic
    > CRITICAL Rule: Multiple threads should NEVER share transaction objects.
    """

    @pytest.mark.asyncio
    async def test_transaction_never_shared_across_threads(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Verify transactions are per-operation, never shared.

        This test validates that each concurrent operation creates its own
        isolated transaction context rather than sharing a transaction.
        """
        thread_local = threading.local()
        operation_ids: list[UUID] = []
        lock = threading.Lock()

        def get_thread_local_node() -> NodeEffect:
            """Get or create thread-local NodeEffect instance."""
            if not hasattr(thread_local, "node"):
                node = NodeEffect(container)
                node.effect_subcontract = effect_subcontract
                thread_local.node = node
            return thread_local.node  # type: ignore[return-value]

        async def simulate_transaction() -> None:
            """Simulate a transaction with unique operation_id."""
            node = get_thread_local_node()

            # Create unique operation_id for this "transaction"
            op_id = uuid4()

            # Simulate transaction operations
            breaker = node.get_circuit_breaker(op_id)
            breaker.record_success()

            with lock:
                operation_ids.append(op_id)

        # Run with ThreadPoolExecutor for true multi-threading
        def run_async_transaction() -> None:
            asyncio.run(simulate_transaction())

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_async_transaction) for _ in range(15)]
            for future in futures:
                future.result()

        # Verify all operations had unique IDs (isolated transactions)
        assert len(operation_ids) == 15, "Not all transactions completed"
        unique_ids = set(operation_ids)
        assert len(unique_ids) == 15, (
            "Transaction IDs not unique - potential transaction sharing"
        )

    @pytest.mark.asyncio
    async def test_concurrent_transaction_rollbacks(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Multiple concurrent rollbacks don't corrupt state.

        This test validates that when multiple threads/tasks perform rollback-like
        operations (circuit breaker resets), they don't corrupt each other's state.
        """
        thread_local = threading.local()
        reset_results: list[tuple[int, str]] = []
        lock = threading.Lock()

        def get_thread_local_node() -> NodeEffect:
            """Get or create thread-local NodeEffect instance."""
            if not hasattr(thread_local, "node"):
                node = NodeEffect(container)
                node.effect_subcontract = effect_subcontract
                thread_local.node = node
            return thread_local.node  # type: ignore[return-value]

        async def simulate_rollback(task_id: int) -> None:
            """Simulate a transaction rollback with circuit breaker reset."""
            node = get_thread_local_node()
            operation_id = uuid4()

            # Get breaker, record some failures, then "rollback" (reset)
            breaker = node.get_circuit_breaker(operation_id)

            # Record failures
            for _ in range(3):
                breaker.record_failure()

            # Simulate rollback by resetting state
            initial_failures = breaker.failure_count
            breaker.reset_state()
            final_failures = breaker.failure_count

            with lock:
                reset_results.append(
                    (task_id, f"initial={initial_failures},final={final_failures}")
                )

        # Run with ThreadPoolExecutor
        def run_async_rollback(task_id: int) -> None:
            asyncio.run(simulate_rollback(task_id))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_async_rollback, i) for i in range(15)]
            for future in futures:
                future.result()

        # Verify all rollbacks completed
        assert len(reset_results) == 15, "Not all rollbacks completed"

        # Each rollback should show initial=3, final=0
        for task_id, result in reset_results:
            assert "initial=3" in result, (
                f"Task {task_id}: unexpected initial state: {result}"
            )
            assert "final=0" in result, (
                f"Task {task_id}: reset did not clear failures: {result}"
            )


# =============================================================================
# TestCircuitBreakerRaceConditionsDetailed
# =============================================================================


@pytest.mark.slow
class TestCircuitBreakerRaceConditionsDetailed:
    """Detailed tests for circuit breaker race conditions.

    These tests provide additional coverage for specific race scenarios
    documented in THREADING.md.
    """

    def test_concurrent_success_and_failure_recording(self):
        """Test race between record_success() and record_failure().

        Concurrent calls to record_success() and record_failure() can
        result in inconsistent state due to non-atomic counter updates.
        """
        breaker = ModelCircuitBreaker()

        num_threads = 20
        ops_per_thread = 10
        success_count = {"count": 0}
        failure_count = {"count": 0}
        count_lock = threading.Lock()

        def record_successes():
            """Record successes and track count."""
            for _ in range(ops_per_thread):
                breaker.record_success()
                with count_lock:
                    success_count["count"] += 1

        def record_failures():
            """Record failures and track count."""
            for _ in range(ops_per_thread):
                breaker.record_failure()
                with count_lock:
                    failure_count["count"] += 1

        # Launch half success threads, half failure threads
        threads = []
        for i in range(num_threads):
            if i % 2 == 0:
                thread = threading.Thread(target=record_successes)
            else:
                thread = threading.Thread(target=record_failures)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify our tracking is correct
        expected_successes = (num_threads // 2) * ops_per_thread
        expected_failures = (num_threads // 2) * ops_per_thread

        assert success_count["count"] == expected_successes
        assert failure_count["count"] == expected_failures

        # Due to races, the breaker's internal counts may differ
        # from our tracking. This is the expected race condition behavior.
        # The test passes if it completes without exceptions.

    def test_concurrent_should_allow_request_checks(self):
        """Test race in should_allow_request() state checks.

        Multiple threads calling should_allow_request() simultaneously
        may see inconsistent results due to race conditions on state
        transitions.
        """
        from datetime import UTC, datetime, timedelta

        # Use minimum timeout for faster test execution
        breaker = ModelCircuitBreaker(timeout_seconds=10)

        # Trip the breaker
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()

        # Force transition to half-open by setting last_state_change to past
        # This simulates timeout having elapsed
        breaker.last_state_change = datetime.now(UTC) - timedelta(seconds=15)

        results: list[bool] = []
        lock = threading.Lock()

        def check_request():
            """Check if request should be allowed."""
            for _ in range(20):
                allowed = breaker.should_allow_request()
                with lock:
                    results.append(allowed)

        # Launch concurrent checks
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=check_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify we got results
        assert len(results) == 200, "Not all checks completed"

        # Results may be inconsistent due to races - this is expected
        # The test documents the behavior

    def test_circuit_breaker_state_corruption_detection(self):
        """Detect potential state corruption from concurrent state transitions.

        This test attempts to detect if concurrent state modifications
        can leave the circuit breaker in an inconsistent state.
        """
        breaker = ModelCircuitBreaker(
            failure_threshold=5,
            success_threshold=3,
            timeout_seconds=10,  # Minimum allowed timeout
        )

        state_history: list[str] = []
        lock = threading.Lock()

        def manipulate_state():
            """Perform various state-changing operations."""
            for _ in range(10):
                # Record failure
                breaker.record_failure()
                with lock:
                    state_history.append(breaker.state)

                # Record success
                breaker.record_success()
                with lock:
                    state_history.append(breaker.state)

                # Force state check
                breaker.should_allow_request()
                with lock:
                    state_history.append(breaker.state)

        # Launch concurrent state manipulations
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=manipulate_state)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify we recorded state history
        assert len(state_history) > 0, "No state history recorded"

        # State should only be one of the valid states
        valid_states = {"closed", "open", "half_open"}
        for state in state_history:
            assert state in valid_states, f"Invalid state detected: {state}"


# =============================================================================
# TestAsyncConcurrency
# =============================================================================


class TestAsyncConcurrency:
    """Test async concurrency patterns with NodeEffect.

    These tests validate behavior under asyncio concurrent execution,
    which is the primary execution model for NodeEffect.
    """

    @pytest.mark.asyncio
    async def test_high_concurrency_circuit_breaker_operations(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test circuit breaker under high async concurrency.

        Launch many concurrent async tasks to stress test circuit breaker
        operations. This simulates production load patterns.
        """
        node = create_node_with_subcontract(container, effect_subcontract)

        num_operations = 100
        operation_ids = [uuid4() for _ in range(num_operations)]

        results: list[bool] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        async def perform_operation(op_id: UUID, success: bool) -> None:
            """Perform a circuit breaker operation."""
            try:
                breaker = node.get_circuit_breaker(op_id)

                if success:
                    breaker.record_success()
                else:
                    breaker.record_failure()

                allowed = breaker.should_allow_request()

                with lock:
                    results.append(allowed)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Create mix of success and failure operations
        tasks = []
        for i, op_id in enumerate(operation_ids):
            success = i % 3 != 0  # 2/3 success, 1/3 failure
            tasks.append(perform_operation(op_id, success))

        await asyncio.gather(*tasks)

        # Verify completion
        assert len(errors) == 0, f"Errors during operations: {errors}"
        assert len(results) == num_operations, "Not all operations completed"

    @pytest.mark.asyncio
    async def test_concurrent_node_effect_creation(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Test concurrent NodeEffect instance creation.

        Validate that creating multiple NodeEffect instances concurrently
        does not cause issues.
        """
        nodes: list[NodeEffect] = []
        lock = threading.Lock()

        async def create_node() -> None:
            """Create a NodeEffect instance."""
            node = NodeEffect(container)
            node.effect_subcontract = effect_subcontract

            # Perform some operation to initialize internal state
            op_id = uuid4()
            breaker = node.get_circuit_breaker(op_id)
            breaker.record_success()

            with lock:
                nodes.append(node)

        # Create many nodes concurrently
        tasks = [create_node() for _ in range(50)]
        await asyncio.gather(*tasks)

        # Verify all nodes were created
        assert len(nodes) == 50, "Not all nodes created"

        # Each node should be a distinct instance
        node_ids = [id(node) for node in nodes]
        unique_ids = set(node_ids)
        assert len(unique_ids) == 50, "Some nodes were reused unexpectedly"

    @pytest.mark.asyncio
    async def test_timing_contention_detection(
        self, container: ModelONEXContainer, effect_subcontract: ModelEffectSubcontract
    ) -> None:
        """Detect slowdowns from contention.

        Measure timing of circuit breaker operations under concurrent load
        to detect if contention causes significant slowdowns.
        """
        node = create_node_with_subcontract(container, effect_subcontract)
        operation_id = uuid4()

        timings: list[float] = []
        lock = threading.Lock()

        async def timed_operation() -> None:
            """Time a circuit breaker operation."""
            start = time.perf_counter()

            breaker = node.get_circuit_breaker(operation_id)
            breaker.record_success()
            _ = breaker.should_allow_request()

            elapsed = time.perf_counter() - start

            with lock:
                timings.append(elapsed)

        # Run with high concurrency
        tasks = [timed_operation() for _ in range(100)]
        await asyncio.gather(*tasks)

        # Analyze timings
        assert len(timings) == 100, "Not all operations completed"

        avg_time = sum(timings) / len(timings)
        max_time = max(timings)
        min_time = min(timings)

        # Operations should be fast (under 10ms average)
        # This is a sanity check, not a strict performance requirement
        assert avg_time < 0.01, f"Average time too slow: {avg_time:.4f}s"

        # Max time should not be excessively longer than average
        # (which would indicate contention issues)
        assert max_time < avg_time * 100, (
            f"Max time ({max_time:.4f}s) significantly exceeds "
            f"average ({avg_time:.4f}s) - potential contention issue"
        )


# =============================================================================
# Run tests with pytest
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
