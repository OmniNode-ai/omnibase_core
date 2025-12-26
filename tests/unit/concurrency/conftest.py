"""
Shared fixtures for concurrency test suite.

This module provides reusable pytest fixtures for testing thread safety
and concurrency patterns across all four ONEX node types (Effect, Compute,
Reducer, Orchestrator).

Thread Safety Context:
    Most ONEX node components are NOT thread-safe by default. These fixtures
    help test and validate concurrency patterns documented in THREADING.md.

Fixture Categories:
    - Container fixtures: Mock ModelONEXContainer for node initialization
    - Thread pool fixtures: Configurable ThreadPoolExecutor instances
    - Async task fixtures: Helpers for concurrent async task execution
    - Race condition detection: Utilities for detecting threading violations
    - Thread-local factory: Factory for creating thread-local node instances
    - Metrics collection: Capture execution times and concurrency metrics

Usage Pattern:
    Fixtures are auto-discovered by pytest. Use them as function parameters::

        async def test_concurrent_compute(
            mock_container,
            thread_pool,
            thread_local_node_factory,
        ):
            # Test concurrent node execution
            pass

Related:
    - docs/guides/THREADING.md: Thread safety documentation
    - tests/fixtures/isolation.py: Test isolation fixtures
    - tests/unit/container/conftest.py: Container test fixtures

Thread Safety Reference (from THREADING.md):
    - NodeCompute: NOT thread-safe (cache operations not atomic)
    - NodeEffect: NOT thread-safe (circuit breaker state corruption)
    - NodeReducer: NOT thread-safe (FSM state is mutable)
    - NodeOrchestrator: NOT thread-safe (workflow state is mutable)
    - ModelONEXContainer: Thread-safe (read-only after initialization)
    - Pydantic Models: Thread-safe (immutable after creation)
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.nodes import (
        NodeCompute,
        NodeEffect,
        NodeOrchestrator,
        NodeReducer,
    )


# Type variable for generic node types
T = TypeVar("T")
NodeT = TypeVar(
    "NodeT", bound="NodeCompute | NodeEffect | NodeReducer | NodeOrchestrator"
)


# =============================================================================
# Container Fixtures
# =============================================================================


@pytest.fixture
def mock_container() -> Generator[MagicMock, None, None]:
    """
    Create a mock ModelONEXContainer for node initialization.

    This fixture provides a mock container that satisfies the interface
    requirements for node constructors without requiring actual service
    registration. The container is configured with common protocol mocks.

    Returns:
        MagicMock: A mock container with pre-configured protocol services.

    Note:
        The mock container is thread-safe as it's read-only after creation
        (matching ModelONEXContainer's thread safety guarantee).

    Usage:
        def test_node_init(mock_container):
            node = NodeCompute(mock_container)
            assert node is not None
    """
    container = MagicMock(
        spec=["get_service", "get_service_optional", "compute_cache_config"]
    )

    # Configure common protocol returns
    mock_logger = MagicMock()
    mock_event_bus = MagicMock()
    mock_metrics = MagicMock()

    def get_service_side_effect(
        protocol_type: type[Any], service_name: str | None = None
    ) -> Any:
        """Return mock services based on protocol type name."""
        protocol_name = getattr(protocol_type, "__name__", str(protocol_type))
        if "Logger" in protocol_name:
            return mock_logger
        elif "EventBus" in protocol_name:
            return mock_event_bus
        elif "Metrics" in protocol_name:
            return mock_metrics
        return MagicMock()

    container.get_service.side_effect = get_service_side_effect
    container.get_service_optional.side_effect = lambda *args, **kwargs: None

    # Configure compute cache config with defaults
    mock_cache_config = MagicMock()
    mock_cache_config.max_size = 1000
    mock_cache_config.default_ttl_minutes = 30
    container.compute_cache_config = mock_cache_config

    return container


@pytest.fixture
def minimal_mock_container() -> Generator[MagicMock, None, None]:
    """
    Create a minimal mock container for lightweight testing.

    This fixture provides the absolute minimum mock required for node
    initialization without any protocol configuration.

    Returns:
        MagicMock: A minimal mock container.

    Usage:
        def test_basic_init(minimal_mock_container):
            # For tests that don't need protocol mocks
            pass
    """
    container = MagicMock()
    container.get_service.return_value = MagicMock()
    container.get_service_optional.return_value = None

    mock_cache_config = MagicMock()
    mock_cache_config.max_size = 100
    mock_cache_config.default_ttl_minutes = 5
    container.compute_cache_config = mock_cache_config

    return container


# =============================================================================
# Thread Pool Fixtures
# =============================================================================


@pytest.fixture
def thread_pool() -> Generator[ThreadPoolExecutor, None, None]:
    """
    Create a configurable ThreadPoolExecutor with 10 workers.

    Default configuration for concurrent testing with proper cleanup.
    The executor is properly shut down after test completion.

    Returns:
        ThreadPoolExecutor: A pool with 10 worker threads.

    Usage:
        def test_concurrent_ops(thread_pool):
            futures = [thread_pool.submit(work) for _ in range(10)]
            results = [f.result() for f in futures]
    """
    executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="test_worker")
    try:
        yield executor
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


@pytest.fixture
def thread_pool_20() -> Generator[ThreadPoolExecutor, None, None]:
    """
    Create a ThreadPoolExecutor with 20 workers for high-contention tests.

    Returns:
        ThreadPoolExecutor: A pool with 20 worker threads.

    Usage:
        def test_high_contention(thread_pool_20):
            # High-contention concurrent testing
            pass
    """
    executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="test_worker_20")
    try:
        yield executor
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


@pytest.fixture
def thread_pool_4() -> Generator[ThreadPoolExecutor, None, None]:
    """
    Create a ThreadPoolExecutor with 4 workers for lighter testing.

    Returns:
        ThreadPoolExecutor: A pool with 4 worker threads.

    Usage:
        def test_light_concurrent(thread_pool_4):
            # Lighter concurrent testing
            pass
    """
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="test_worker_4")
    try:
        yield executor
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


# =============================================================================
# Threading Synchronization Fixtures
# =============================================================================


@pytest.fixture
def barrier_10() -> threading.Barrier:
    """
    Create a threading barrier for synchronizing 10 threads.

    Returns:
        threading.Barrier: A barrier configured for 10 parties.

    Usage:
        Used in concurrent stress tests to ensure all threads
        start their operations simultaneously.
    """
    return threading.Barrier(10)


@pytest.fixture
def barrier_20() -> threading.Barrier:
    """
    Create a threading barrier for synchronizing 20 threads.

    Returns:
        threading.Barrier: A barrier configured for 20 parties.

    Usage:
        Used in high-contention stress tests to synchronize
        20 concurrent operations.
    """
    return threading.Barrier(20)


@pytest.fixture
def thread_start_event() -> threading.Event:
    """
    Create a threading Event for coordinating thread starts.

    Returns:
        threading.Event: An event for thread coordination.

    Usage:
        def test_coordinated_start(thread_start_event, thread_pool):
            def worker():
                thread_start_event.wait()  # All workers wait here
                # Perform concurrent work
                pass

            futures = [thread_pool.submit(worker) for _ in range(10)]
            thread_start_event.set()  # Release all workers at once
            results = [f.result() for f in futures]
    """
    return threading.Event()


# =============================================================================
# Async Task Fixtures
# =============================================================================


@dataclass
class AsyncTaskLauncher:
    """
    Helper class for launching concurrent async tasks.

    Attributes:
        results: List of results from completed tasks.
        errors: List of exceptions from failed tasks.
        execution_times: List of execution times in seconds.
        task_count: Number of tasks launched.
    """

    results: list[Any] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)
    execution_times: list[float] = field(default_factory=list)
    task_count: int = 0

    async def launch_concurrent(
        self,
        coro_factory: Callable[[], Any],
        count: int = 10,
        timeout: float | None = 30.0,
    ) -> list[Any]:
        """
        Launch N concurrent async tasks and collect results.

        Args:
            coro_factory: Callable that returns a coroutine to execute.
            count: Number of concurrent tasks to launch (default: 10).
            timeout: Optional timeout in seconds for all tasks.

        Returns:
            List of results from successful tasks.

        Raises:
            asyncio.TimeoutError: If timeout is exceeded.
        """
        self.task_count = count
        self.results = []
        self.errors = []
        self.execution_times = []

        async def timed_task(index: int) -> tuple[int, Any, float]:
            """Execute task with timing."""
            start = time.perf_counter()
            try:
                result = await coro_factory()
                elapsed = time.perf_counter() - start
                return (index, result, elapsed)
            except Exception as e:
                elapsed = time.perf_counter() - start
                self.errors.append(e)
                return (index, None, elapsed)

        tasks = [timed_task(i) for i in range(count)]

        if timeout:
            completed = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout,
            )
        else:
            completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                self.errors.append(item)
            elif isinstance(item, tuple) and len(item) == 3:
                _, result, elapsed = item
                if result is not None:
                    self.results.append(result)
                self.execution_times.append(elapsed)

        return self.results

    @property
    def success_count(self) -> int:
        """Number of successful task completions."""
        return len(self.results)

    @property
    def error_count(self) -> int:
        """Number of task failures."""
        return len(self.errors)

    @property
    def avg_execution_time(self) -> float:
        """Average execution time in seconds."""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times)


@pytest.fixture
def async_task_launcher() -> AsyncTaskLauncher:
    """
    Create an async task launcher for concurrent testing.

    Returns:
        AsyncTaskLauncher: Helper for launching concurrent async tasks.

    Usage:
        async def test_concurrent_async(async_task_launcher):
            async def work():
                await asyncio.sleep(0.01)
                return "done"

            results = await async_task_launcher.launch_concurrent(work, count=20)
            assert len(results) == 20
            assert async_task_launcher.error_count == 0
    """
    return AsyncTaskLauncher()


# =============================================================================
# Race Condition Detection
# =============================================================================


@dataclass
class RaceConditionDetector:
    """
    Detector for identifying race conditions in concurrent code.

    This detector tracks concurrent access patterns and can identify
    potential race conditions based on overlapping access windows.

    Attributes:
        access_log: Log of (thread_id, operation, timestamp) tuples.
        detected_races: List of detected race condition descriptions.
        access_counts: Counter of accesses per operation type.
    """

    access_log: list[tuple[int, str, float]] = field(default_factory=list)
    detected_races: list[str] = field(default_factory=list)
    access_counts: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_access(self, operation: str) -> None:
        """
        Record an access for race condition analysis.

        Args:
            operation: Name of the operation being performed.
        """
        thread_id = threading.current_thread().ident or 0
        timestamp = time.perf_counter()

        with self._lock:
            self.access_log.append((thread_id, operation, timestamp))
            self.access_counts[operation] = self.access_counts.get(operation, 0) + 1

    def analyze_races(self, window_ms: float = 1.0) -> list[str]:
        """
        Analyze access log for potential race conditions.

        A race condition is detected when multiple threads access
        the same operation within the specified time window.

        Args:
            window_ms: Time window in milliseconds for race detection.

        Returns:
            List of race condition descriptions.
        """
        self.detected_races = []
        window_sec = window_ms / 1000.0

        with self._lock:
            # Group accesses by operation
            by_operation: dict[str, list[tuple[int, float]]] = {}
            for thread_id, operation, timestamp in self.access_log:
                if operation not in by_operation:
                    by_operation[operation] = []
                by_operation[operation].append((thread_id, timestamp))

            # Check for overlapping accesses from different threads
            for operation, accesses in by_operation.items():
                accesses.sort(key=lambda x: x[1])  # Sort by timestamp

                for i, (tid1, ts1) in enumerate(accesses):
                    for tid2, ts2 in accesses[i + 1 :]:
                        if tid1 != tid2 and abs(ts2 - ts1) < window_sec:
                            race_desc = (
                                f"Race on '{operation}': "
                                f"thread {tid1} and thread {tid2} "
                                f"within {abs(ts2 - ts1) * 1000:.3f}ms"
                            )
                            self.detected_races.append(race_desc)

        return self.detected_races

    @property
    def has_races(self) -> bool:
        """Whether any race conditions were detected."""
        return len(self.detected_races) > 0

    @property
    def unique_threads(self) -> set[int]:
        """Set of unique thread IDs that accessed resources."""
        return {tid for tid, _, _ in self.access_log}

    def reset(self) -> None:
        """Reset all tracking state."""
        with self._lock:
            self.access_log.clear()
            self.detected_races.clear()
            self.access_counts.clear()


@pytest.fixture
def race_detector() -> RaceConditionDetector:
    """
    Create a race condition detector for concurrent testing.

    Returns:
        RaceConditionDetector: Detector for identifying race conditions.

    Usage:
        def test_race_detection(race_detector, thread_pool):
            def worker():
                race_detector.record_access("cache_update")
                # Perform operation
                race_detector.record_access("cache_read")

            futures = [thread_pool.submit(worker) for _ in range(10)]
            [f.result() for f in futures]

            races = race_detector.analyze_races(window_ms=5.0)
            # Expect races in non-thread-safe code
            assert len(races) > 0
    """
    return RaceConditionDetector()


# =============================================================================
# Thread-Local Node Factory
# =============================================================================


class ThreadLocalNodeFactory[NodeT]:
    """
    Factory for creating thread-local node instances.

    This implements the recommended pattern from THREADING.md for safe
    concurrent node usage. Each thread gets its own isolated node instance.

    Type Parameters:
        NodeT: The node type (NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator).

    Attributes:
        node_class: The node class to instantiate.
        container: The container to pass to node constructors.
        instances: Dict mapping thread IDs to node instances.
    """

    def __init__(
        self,
        node_class: type[NodeT],
        container: ModelONEXContainer | MagicMock,
        setup_fn: Callable[[NodeT], None] | None = None,
    ) -> None:
        """
        Initialize the thread-local factory.

        Args:
            node_class: The node class to instantiate.
            container: The container to pass to node constructors.
            setup_fn: Optional setup function to call on each new instance.
        """
        self._node_class = node_class
        self._container = container
        self._setup_fn = setup_fn
        self._thread_local = threading.local()
        self._instances: dict[int, NodeT] = {}
        self._lock = threading.Lock()

    def get_node(self) -> NodeT:
        """
        Get or create a thread-local node instance.

        Returns:
            NodeT: The node instance for the current thread.

        Thread Safety:
            Each thread gets its own instance, ensuring no state sharing.
        """
        thread_id = threading.current_thread().ident or 0
        key = f"node_{id(self._node_class)}"

        if not hasattr(self._thread_local, key):
            # Create new instance for this thread
            node = self._node_class(self._container)

            if self._setup_fn:
                self._setup_fn(node)

            setattr(self._thread_local, key, node)

            # Track for cleanup and inspection
            with self._lock:
                self._instances[thread_id] = node

        return getattr(self._thread_local, key)

    @property
    def instance_count(self) -> int:
        """Number of node instances created across all threads."""
        with self._lock:
            return len(self._instances)

    @property
    def thread_ids(self) -> list[int]:
        """List of thread IDs that have node instances."""
        with self._lock:
            return list(self._instances.keys())

    def get_all_instances(self) -> list[NodeT]:
        """Get all node instances (for inspection/cleanup)."""
        with self._lock:
            return list(self._instances.values())


@pytest.fixture
def thread_local_node_factory(
    mock_container: MagicMock,
) -> Callable[
    [type[NodeT], Callable[[NodeT], None] | None], ThreadLocalNodeFactory[NodeT]
]:
    """
    Create a factory function for thread-local node factories.

    Returns:
        A factory function that creates ThreadLocalNodeFactory instances.

    Usage:
        def test_thread_local_nodes(thread_local_node_factory, thread_pool):
            factory = thread_local_node_factory(NodeCompute)

            def worker():
                node = factory.get_node()
                # Each thread gets its own node instance
                return id(node)

            futures = [thread_pool.submit(worker) for _ in range(10)]
            node_ids = [f.result() for f in futures]

            # Verify each thread has unique instance
            assert len(set(node_ids)) == factory.instance_count
    """

    def create_factory(
        node_class: type[NodeT],
        setup_fn: Callable[[NodeT], None] | None = None,
    ) -> ThreadLocalNodeFactory[NodeT]:
        return ThreadLocalNodeFactory(node_class, mock_container, setup_fn)

    return create_factory


# =============================================================================
# Metrics Collection
# =============================================================================


@dataclass
class ConcurrencyMetrics:
    """
    Collector for concurrency testing metrics.

    Attributes:
        operation_times: Dict mapping operation names to list of durations.
        thread_counts: Dict mapping operation names to number of unique threads.
        error_counts: Dict mapping operation names to error counts.
        total_operations: Total number of operations recorded.
    """

    operation_times: dict[str, list[float]] = field(default_factory=dict)
    thread_counts: dict[str, set[int]] = field(default_factory=dict)
    error_counts: dict[str, int] = field(default_factory=dict)
    total_operations: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_operation(
        self,
        name: str,
        duration_seconds: float,
        error: bool = False,
    ) -> None:
        """
        Record a single operation's metrics.

        Args:
            name: Name of the operation.
            duration_seconds: How long the operation took.
            error: Whether the operation resulted in an error.
        """
        thread_id = threading.current_thread().ident or 0

        with self._lock:
            if name not in self.operation_times:
                self.operation_times[name] = []
                self.thread_counts[name] = set()
                self.error_counts[name] = 0

            self.operation_times[name].append(duration_seconds)
            self.thread_counts[name].add(thread_id)
            if error:
                self.error_counts[name] += 1
            self.total_operations += 1

    def get_stats(self, name: str) -> dict[str, float | int]:
        """
        Get statistics for a specific operation.

        Args:
            name: Name of the operation.

        Returns:
            Dict with min, max, avg, count, unique_threads, error_count.
        """
        with self._lock:
            times = self.operation_times.get(name, [])
            if not times:
                return {
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0,
                    "unique_threads": 0,
                    "error_count": 0,
                }

            return {
                "min": min(times),
                "max": max(times),
                "avg": sum(times) / len(times),
                "count": len(times),
                "unique_threads": len(self.thread_counts.get(name, set())),
                "error_count": self.error_counts.get(name, 0),
            }

    def get_all_stats(self) -> dict[str, dict[str, float | int]]:
        """Get statistics for all recorded operations."""
        with self._lock:
            return {name: self.get_stats(name) for name in self.operation_times}

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.operation_times.clear()
            self.thread_counts.clear()
            self.error_counts.clear()
            self.total_operations = 0


@pytest.fixture
def concurrency_metrics() -> ConcurrencyMetrics:
    """
    Create a metrics collector for concurrency testing.

    Returns:
        ConcurrencyMetrics: Collector for execution times and concurrency stats.

    Usage:
        def test_with_metrics(concurrency_metrics, thread_pool):
            def worker():
                start = time.perf_counter()
                try:
                    # Perform operation
                    pass
                    concurrency_metrics.record_operation(
                        "my_op",
                        time.perf_counter() - start,
                    )
                except Exception:
                    concurrency_metrics.record_operation(
                        "my_op",
                        time.perf_counter() - start,
                        error=True,
                    )

            futures = [thread_pool.submit(worker) for _ in range(10)]
            [f.result() for f in futures]

            stats = concurrency_metrics.get_stats("my_op")
            assert stats["error_count"] == 0
            assert stats["unique_threads"] == 10
    """
    return ConcurrencyMetrics()


# =============================================================================
# Event Loop Fixture
# =============================================================================


@pytest.fixture
def isolated_event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Provide an isolated event loop for async concurrency testing.

    This creates a new event loop, sets it as current, and cleans up
    after the test. Essential for tests that need isolated async state.

    Returns:
        The new event loop.

    Usage:
        async def test_async_concurrent(isolated_event_loop, async_task_launcher):
            # Uses fresh isolated event loop
            results = await async_task_launcher.launch_concurrent(
                work_coro, count=10
            )
    """
    # Create fresh loop
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    try:
        yield new_loop
    finally:
        # Clean up the new loop
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(new_loop)
            for task in pending:
                task.cancel()

            # Give tasks a chance to handle cancellation
            if pending:
                new_loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            new_loop.close()
        except Exception:
            # Best effort cleanup
            pass


# =============================================================================
# Debug Thread Safety Environment
# =============================================================================


@pytest.fixture
def enable_thread_safety_debug() -> Generator[None, None, None]:
    """
    Enable ONEX debug thread safety validation for the test.

    This fixture sets ONEX_DEBUG_THREAD_SAFETY=1 to enable runtime
    thread safety validation in NodeEffect and related components.

    Usage:
        def test_thread_violation_detected(
            enable_thread_safety_debug,
            mock_container,
        ):
            # Thread safety violations will raise ModelOnexError
            # with THREAD_SAFETY_VIOLATION error code
            pass

    See Also:
        - docs/guides/THREADING.md: Built-in Debug Mode Thread Safety Validation
    """
    import os

    original_value = os.environ.get("ONEX_DEBUG_THREAD_SAFETY")
    os.environ["ONEX_DEBUG_THREAD_SAFETY"] = "1"

    try:
        yield
    finally:
        if original_value is None:
            os.environ.pop("ONEX_DEBUG_THREAD_SAFETY", None)
        else:
            os.environ["ONEX_DEBUG_THREAD_SAFETY"] = original_value


# =============================================================================
# Thread Safety Test Utilities
# =============================================================================


@dataclass
class ThreadSafetyTestContext:
    """
    Context for thread safety testing with shared state tracking.

    Provides utilities for tracking shared state access across threads
    and detecting violations of thread safety guarantees.
    """

    shared_counter: int = 0
    access_history: list[tuple[int, str, int]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _no_lock_counter: int = 0  # Deliberately unprotected for race testing

    def increment_safe(self) -> int:
        """Thread-safe counter increment."""
        with self._lock:
            self.shared_counter += 1
            thread_id = threading.current_thread().ident or 0
            self.access_history.append((thread_id, "increment", self.shared_counter))
            return self.shared_counter

    def increment_unsafe(self) -> int:
        """Deliberately unsafe counter increment for race condition testing."""
        # Read-modify-write without lock - INTENTIONALLY UNSAFE
        current = self._no_lock_counter
        # Yield to increase race probability
        time.sleep(0.0001)
        self._no_lock_counter = current + 1
        return self._no_lock_counter

    def check_consistency(self) -> list[str]:
        """Check for inconsistencies indicating race conditions."""
        with self._lock:
            self.violations = []

            # Check if unsafe counter matches expected
            expected = len([h for h in self.access_history if h[1] == "increment"])
            if self._no_lock_counter < expected:
                self.violations.append(
                    f"Counter mismatch: expected >= {expected}, got {self._no_lock_counter}"
                )

            return self.violations


@pytest.fixture
def thread_safety_context() -> ThreadSafetyTestContext:
    """
    Create a thread safety test context with shared state.

    Returns:
        ThreadSafetyTestContext: Context for testing thread safety patterns.

    Usage:
        def test_unsafe_increment(thread_safety_context, thread_pool):
            def worker():
                for _ in range(100):
                    thread_safety_context.increment_unsafe()

            futures = [thread_pool.submit(worker) for _ in range(10)]
            [f.result() for f in futures]

            # Expect race conditions with unsafe increment
            violations = thread_safety_context.check_consistency()
            # violations will likely be non-empty due to races
    """
    return ThreadSafetyTestContext()
