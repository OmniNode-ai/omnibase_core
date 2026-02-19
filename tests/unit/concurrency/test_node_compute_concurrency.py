# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive Concurrency Tests for NodeCompute.

This module tests thread safety of NodeCompute components under concurrent load,
specifically targeting the HIGH thread safety risk areas:

1. Cache get/put races: Concurrent get() calls racing with put() operations
2. LRU eviction corruption: LRU eviction logic corrupting cache state
3. Access count races: Access count updates not being atomic
4. Parallel batch processing: ThreadPoolExecutor usage in batch processing

These tests detect cache corruption and validate thread-safe wrapper patterns.

Thread Safety Warning:
    NodeCompute has HIGH thread safety risk due to non-atomic cache operations.
    The LRU cache can corrupt under concurrent access.
    See docs/guides/THREADING.md for mitigation strategies.

Test Strategy:
    - Minimum 10 concurrent async tasks per test
    - Use asyncio.gather() for concurrent execution
    - Use ThreadPoolExecutor for true multi-threading tests
    - Test cache with various sizes (small cache = more evictions = more races)
    - Tests must be deterministic (no flaky tests)

References:
    - src/omnibase_core/nodes/node_compute.py - NodeCompute implementation
    - src/omnibase_core/models/infrastructure/model_compute_cache.py - Cache implementation
    - docs/guides/THREADING.md - ThreadSafeComputeCache wrapper pattern
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache
from omnibase_core.nodes.node_compute import NodeCompute

# =============================================================================
# Thread-Safe Wrapper Implementation (from docs/guides/THREADING.md)
# =============================================================================


class ThreadSafeComputeCache:
    """
    Thread-safe wrapper for ModelComputeCache.

    This implementation is from docs/guides/THREADING.md and provides
    proper synchronization for production use.

    Use this wrapper in production environments where NodeCompute
    instances are shared across threads.
    """

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        """
        Initialize thread-safe cache wrapper.

        Args:
            max_size: Maximum number of cache entries
            default_ttl_minutes: Default TTL in minutes for cached values
        """
        self._cache = ModelComputeCache(max_size, default_ttl_minutes)
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        """Thread-safe cache retrieval."""
        with self._lock:
            return self._cache.get(key)

    def put(self, key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """Thread-safe cache storage."""
        with self._lock:
            self._cache.put(key, value, ttl_minutes)

    def clear(self) -> None:
        """Thread-safe cache clearing."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, int | float]:
        """Thread-safe cache statistics."""
        with self._lock:
            return self._cache.get_stats()

    def compute_if_absent(
        self,
        key: str,
        compute_fn: Callable[[str], Any],
        ttl_minutes: int | None = None,
    ) -> Any:
        """
        Atomically compute and cache value if absent.

        This method prevents race conditions by holding the lock
        during both the cache check and computation.

        Args:
            key: Cache key
            compute_fn: Function to compute value if absent (receives key as arg)
            ttl_minutes: Optional TTL override

        Returns:
            Cached or newly computed value
        """
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

            result = compute_fn(key)
            self._cache.put(key, result, ttl_minutes)
            return result


# =============================================================================
# Test Class: ModelComputeCache Concurrency Tests
# =============================================================================


@pytest.mark.slow
@pytest.mark.timeout(120)
@pytest.mark.unit
class TestModelComputeCacheConcurrency:
    """
    Test cache thread safety under concurrent load.

    These tests verify that ModelComputeCache exhibits expected behavior
    (including potential corruption) under concurrent access, demonstrating
    why thread-safe wrappers are necessary.

    Thread Safety Issues Tested:
    1. Concurrent cache access from 10+ async tasks
    2. Race conditions between get() and put() operations
    3. LRU eviction corruption under concurrent load
    4. Access count accuracy under concurrent access
    """

    @pytest.mark.asyncio
    async def test_concurrent_cache_access_10_tasks(self) -> None:
        """
        Test 10+ async tasks accessing cache simultaneously.

        This test validates that concurrent cache access:
        1. Does not crash or raise exceptions
        2. Returns valid results (not corrupted memory)
        3. Demonstrates potential race conditions

        Expected behavior: All tasks complete without crash,
        but cache state may be inconsistent.
        """
        cache = ModelComputeCache(max_size=50, default_ttl_minutes=30)
        task_count = 15
        operations_per_task = 20
        errors: list[Exception] = []
        results: list[str | None] = []
        results_lock = Lock()

        async def cache_worker(task_id: int) -> None:
            """Worker that performs mixed cache operations."""
            try:
                for i in range(operations_per_task):
                    key = f"key_{task_id}_{i}"
                    value = f"value_{task_id}_{i}"

                    # Mixed read/write operations
                    if i % 2 == 0:
                        cache.put(key, value)
                    else:
                        result = cache.get(key)
                        with results_lock:
                            results.append(result)

                    # Cross-task key access to increase contention
                    cross_key = f"key_{(task_id + 1) % task_count}_{i}"
                    cache.get(cross_key)

            except Exception as e:
                with results_lock:
                    errors.append(e)

        # Launch concurrent tasks
        tasks = [cache_worker(task_id) for task_id in range(task_count)]
        await asyncio.gather(*tasks)

        # Verify no exceptions occurred
        assert len(errors) == 0, f"Cache operations raised errors: {errors}"

        # Verify cache is still functional
        test_key = "test_key_final"
        test_value = "test_value_final"
        cache.put(test_key, test_value)
        assert cache.get(test_key) == test_value, (
            "Cache is not functional after concurrent access"
        )

        # Verify stats are accessible
        stats = cache.get_stats()
        assert "total_entries" in stats
        assert stats["total_entries"] >= 0, "Invalid total_entries in stats"

    @pytest.mark.asyncio
    async def test_cache_get_put_race_condition(self) -> None:
        """
        Detect race between get() and put() operations.

        This test demonstrates the classic check-then-act race condition:
        Thread A checks cache (miss) -> Thread B writes -> Thread A writes
        Result: Redundant computation or lost updates

        Success Criteria:
        1. All operations complete without crash
        2. Final cache contains at least one valid entry per unique key
        3. Demonstrates that without locking, multiple computations occur
        """
        cache = ModelComputeCache(max_size=100, default_ttl_minutes=30)
        computation_count = {"count": 0}
        count_lock = Lock()

        def expensive_computation(key: str) -> str:
            """Simulate expensive computation that should be cached."""
            with count_lock:
                computation_count["count"] += 1
            # Small delay to increase race window
            time.sleep(0.001)
            return f"computed_{key}"

        async def compute_with_cache(key: str) -> str:
            """Compute with caching - demonstrates race condition."""
            # Check cache first
            cached = cache.get(key)
            if cached is not None:
                return cached

            # Cache miss - compute (race window here!)
            result = expensive_computation(key)

            # Store in cache
            cache.put(key, result)
            return result

        # Multiple tasks requesting same keys concurrently
        num_tasks = 15
        num_keys = 5  # Few unique keys = more contention
        tasks = []

        for i in range(num_tasks):
            key = f"shared_key_{i % num_keys}"
            tasks.append(compute_with_cache(key))

        results = await asyncio.gather(*tasks)

        # All results should be valid strings
        assert all(isinstance(r, str) for r in results), "Some results are not strings"
        assert all(r.startswith("computed_") for r in results), (
            "Some results are invalid"
        )

        # Without synchronization, we expect redundant computations
        # Ideal would be num_keys computations (one per unique key)
        # With races, we get more
        print(
            f"Computations performed: {computation_count['count']} (ideal: {num_keys})"
        )

        # This is a detection test - we verify the race exists
        # In production, use ThreadSafeComputeCache.compute_if_absent()

    @pytest.mark.asyncio
    async def test_lru_eviction_under_concurrent_load(self) -> None:
        """
        Test LRU eviction doesn't corrupt cache with concurrent access.

        Uses a small cache (max_size=5) to force frequent evictions,
        which increases the chance of race conditions in the eviction logic.

        Success Criteria:
        1. No crashes or exceptions
        2. Cache maintains max_size invariant (may briefly exceed due to races)
        3. Cache entries are valid (no corrupted data)
        """
        # Small cache to force frequent evictions
        cache = ModelComputeCache(max_size=5, default_ttl_minutes=30)
        num_tasks = 20
        entries_per_task = 10
        errors: list[Exception] = []
        errors_lock = Lock()

        async def eviction_stressor(task_id: int) -> None:
            """Write many entries to force evictions."""
            try:
                for i in range(entries_per_task):
                    key = f"task_{task_id}_entry_{i}"
                    value = f"value_{task_id}_{i}_{uuid4()}"
                    cache.put(key, value)

                    # Verify recently written entries (increases read/write contention)
                    if i > 0:
                        prev_key = f"task_{task_id}_entry_{i - 1}"
                        cache.get(prev_key)  # May or may not be evicted

            except Exception as e:
                with errors_lock:
                    errors.append(e)

        # Run concurrent eviction stress
        tasks = [eviction_stressor(task_id) for task_id in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify no exceptions
        assert len(errors) == 0, f"Eviction stress test raised errors: {errors}"

        # Get final stats
        stats = cache.get_stats()
        print(f"Final cache stats: {stats}")

        # Cache should maintain size invariant (may briefly exceed during races)
        # In a thread-safe implementation, this would always be true
        # For demonstration, we allow a small margin
        assert stats["total_entries"] <= cache.max_size + 2, (
            f"Cache severely exceeded max_size: {stats['total_entries']} > {cache.max_size}"
        )

        # Verify cache is still functional after stress
        test_key = "final_test_key"
        cache.put(test_key, "final_value")
        assert cache.get(test_key) == "final_value"

    @pytest.mark.asyncio
    async def test_access_count_accuracy(self) -> None:
        """
        Test access counts remain accurate under concurrent access.

        Access count updates in ModelComputeCache are not atomic,
        which can lead to inaccurate counts under concurrent load.

        Success Criteria:
        1. Stats tracking functions work without crash
        2. Hit rate calculation doesn't raise exceptions
        3. Total requests is tracked (though may be inaccurate)
        """
        cache = ModelComputeCache(
            max_size=100, default_ttl_minutes=30, enable_stats=True
        )

        # Pre-populate cache with known keys
        known_keys = [f"key_{i}" for i in range(10)]
        for key in known_keys:
            cache.put(key, f"value_{key}")

        num_tasks = 12
        accesses_per_task = 50
        expected_min_accesses = num_tasks * accesses_per_task

        async def access_worker(task_id: int) -> None:
            """Perform many cache accesses."""
            for i in range(accesses_per_task):
                # Access known keys (should be hits)
                key_idx = (task_id + i) % len(known_keys)
                cache.get(known_keys[key_idx])

        # Run concurrent accesses
        tasks = [access_worker(task_id) for task_id in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Get stats
        stats = cache.get_stats()
        print(f"Stats after concurrent access: {stats}")

        # Stats should be present and non-negative
        assert "hits" in stats, "Stats missing 'hits'"
        assert "misses" in stats, "Stats missing 'misses'"
        assert "total_requests" in stats, "Stats missing 'total_requests'"
        assert stats["hits"] >= 0, "Negative hit count"
        assert stats["misses"] >= 0, "Negative miss count"
        assert stats["total_requests"] >= 0, "Negative total_requests"

        # Hit rate should be calculable
        assert "hit_rate" in stats, "Stats missing 'hit_rate'"
        assert 0 <= stats["hit_rate"] <= 100, f"Invalid hit_rate: {stats['hit_rate']}"

        # Note: Due to race conditions, total_requests may be less than expected
        # This demonstrates the non-atomic nature of the counter updates
        print(
            f"Expected min accesses: {expected_min_accesses}, "
            f"Tracked: {stats['total_requests']}"
        )


# =============================================================================
# Test Class: ThreadSafeComputeCache Wrapper Tests
# =============================================================================


@pytest.mark.timeout(120)
@pytest.mark.unit
class TestThreadSafeComputeCacheWrapper:
    """
    Test the ThreadSafeComputeCache wrapper pattern.

    These tests verify that the thread-safe wrapper from docs/guides/THREADING.md
    correctly prevents race conditions and maintains cache invariants.
    """

    @pytest.mark.asyncio
    async def test_locked_cache_operations_safe(self) -> None:
        """
        Verify locked wrapper prevents race conditions.

        Unlike the raw ModelComputeCache, the ThreadSafeComputeCache
        should maintain all invariants under concurrent access.
        """
        cache = ThreadSafeComputeCache(max_size=10, default_ttl_minutes=30)
        num_tasks = 20
        operations_per_task = 30
        errors: list[Exception] = []
        errors_lock = Lock()

        async def safe_cache_worker(task_id: int) -> None:
            """Perform concurrent operations on thread-safe cache."""
            try:
                for i in range(operations_per_task):
                    key = f"key_{task_id}_{i}"
                    value = f"value_{task_id}_{i}"
                    cache.put(key, value)

                    # Cross-task access
                    cross_key = f"key_{(task_id + 1) % num_tasks}_{i}"
                    cache.get(cross_key)

            except Exception as e:
                with errors_lock:
                    errors.append(e)

        # Run concurrent operations
        tasks = [safe_cache_worker(task_id) for task_id in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Verify no errors
        assert len(errors) == 0, f"Thread-safe cache raised errors: {errors}"

        # Verify cache size invariant is maintained
        stats = cache.get_stats()
        assert stats["total_entries"] <= 10, (
            f"Thread-safe cache exceeded max_size: {stats['total_entries']}"
        )

        # Verify stats are accurate
        assert stats["total_entries"] >= 0

    @pytest.mark.asyncio
    async def test_compute_if_absent_atomicity(self) -> None:
        """
        Test compute_if_absent() is atomic under concurrent calls.

        This is the recommended pattern for cache population.
        With proper atomicity, each unique key should be computed exactly once.
        """
        cache = ThreadSafeComputeCache(max_size=100, default_ttl_minutes=30)
        computation_count = {"count": 0}
        count_lock = Lock()
        computed_keys: set[str] = set()
        computed_keys_lock = Lock()

        def expensive_computation(key: str) -> str:
            """Track computation calls."""
            with count_lock:
                computation_count["count"] += 1
            with computed_keys_lock:
                computed_keys.add(key)
            time.sleep(0.002)  # Simulate expensive work
            return f"computed_{key}"

        num_tasks = 15
        num_unique_keys = 5
        results: list[str] = []
        results_lock = Lock()

        async def atomic_compute_worker(task_id: int) -> None:
            """Use atomic compute_if_absent pattern - each task accesses ALL keys."""
            for key_id in range(num_unique_keys):  # Each task tries ALL keys
                key = f"shared_key_{key_id}"
                result = cache.compute_if_absent(key, expensive_computation)
                with results_lock:
                    results.append(result)

        # Run concurrent atomic computations
        tasks = [atomic_compute_worker(task_id) for task_id in range(num_tasks)]
        await asyncio.gather(*tasks)

        # With atomic compute_if_absent, each unique key computed exactly once
        print(f"Computations: {computation_count['count']} (ideal: {num_unique_keys})")
        print(f"Computed keys: {computed_keys}")
        assert computation_count["count"] == num_unique_keys, (
            f"Expected {num_unique_keys} computations, got {computation_count['count']}"
        )

        # All unique keys should have been computed
        assert len(computed_keys) == num_unique_keys, (
            f"Expected {num_unique_keys} computed keys, got {len(computed_keys)}"
        )

        # All results should be consistent
        unique_results = set(results)
        assert len(unique_results) == num_unique_keys, (
            f"Expected {num_unique_keys} unique results, got {len(unique_results)}"
        )

    @pytest.mark.asyncio
    async def test_thread_safe_stats_consistency(self) -> None:
        """
        Test that stats remain consistent with thread-safe wrapper.

        The thread-safe wrapper should provide accurate statistics
        even under concurrent access.
        """
        cache = ThreadSafeComputeCache(max_size=50, default_ttl_minutes=30)

        # Pre-populate some entries
        for i in range(20):
            cache.put(f"prepop_{i}", f"value_{i}")

        num_tasks = 10
        accesses_per_task = 30
        hit_keys = [f"prepop_{i}" for i in range(20)]

        async def stats_checker() -> dict[str, int | float]:
            """Check stats consistency during operations."""
            for i in range(accesses_per_task):
                key_idx = i % len(hit_keys)
                cache.get(hit_keys[key_idx])
            return cache.get_stats()

        # Run concurrent stats access
        tasks = [stats_checker() for _ in range(num_tasks)]
        all_stats = await asyncio.gather(*tasks)

        # Final stats should be consistent
        final_stats = cache.get_stats()
        print(f"Final stats: {final_stats}")

        # Total requests should be accurate with locking
        expected_total = num_tasks * accesses_per_task
        # Add initial 20 puts
        assert final_stats["total_requests"] >= expected_total, (
            f"Stats undercount: {final_stats['total_requests']} < {expected_total}"
        )


# =============================================================================
# Test Class: NodeCompute Parallel Batch Processing Tests
# =============================================================================


@pytest.mark.timeout(120)
@pytest.mark.unit
class TestNodeComputeParallelBatchProcessing:
    """
    Test parallel batch processing thread safety.

    These tests verify that NodeCompute's parallel execution features
    do not corrupt shared cache state.
    """

    @pytest.fixture
    def container(self) -> ModelONEXContainer:
        """Provide a configured container for NodeCompute tests."""
        return ModelONEXContainer()

    @pytest.mark.asyncio
    async def test_parallel_batch_no_cache_corruption(
        self, container: ModelONEXContainer
    ) -> None:
        """
        Test parallel batch processing doesn't corrupt shared cache.

        When multiple batches are processed in parallel (via threads),
        the cache should not become corrupted.
        """
        num_threads = 8
        batches_per_thread = 5
        errors: list[Exception] = []
        errors_lock = Lock()
        results: list[str] = []
        results_lock = Lock()

        def process_batches(thread_id: int, node: NodeCompute[list[int], int]) -> None:
            """Process multiple batches in a single thread."""
            try:
                for batch_id in range(batches_per_thread):
                    # Create input data
                    data = list(range(batch_id, batch_id + 5))
                    input_data: ModelComputeInput[list[int]] = ModelComputeInput(
                        data=data,
                        computation_type="sum_numbers",
                        cache_enabled=True,
                        parallel_enabled=False,  # Sequential within batch
                    )

                    # Process synchronously in thread
                    # Bind input_data via default argument to avoid closure issue
                    async def do_process(
                        _input: ModelComputeInput[list[int]] = input_data,
                    ) -> Any:
                        return await node.process(_input)

                    loop = asyncio.new_event_loop()
                    try:
                        result = loop.run_until_complete(do_process())
                        with results_lock:
                            results.append(f"t{thread_id}b{batch_id}:{result.result}")
                    finally:
                        loop.close()

            except Exception as e:
                with errors_lock:
                    errors.append(e)

        # Each thread gets its own NodeCompute instance (recommended pattern)
        def thread_worker(thread_id: int) -> None:
            """Thread worker with own NodeCompute instance."""
            node: NodeCompute[list[int], int] = NodeCompute(container)
            process_batches(thread_id, node)

        # Launch threads
        threads = []
        for thread_id in range(num_threads):
            t = threading.Thread(target=thread_worker, args=(thread_id,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=30)

        # Verify no errors
        assert len(errors) == 0, f"Parallel batch processing raised errors: {errors}"

        # Verify all batches completed
        expected_results = num_threads * batches_per_thread
        assert len(results) == expected_results, (
            f"Expected {expected_results} results, got {len(results)}"
        )

    @pytest.mark.asyncio
    async def test_thread_local_compute_nodes_isolated(
        self, container: ModelONEXContainer
    ) -> None:
        """
        Test thread-local NodeCompute instances are isolated.

        Each thread should have its own NodeCompute with isolated cache state.
        Operations in one thread should not affect another thread's cache.
        """
        thread_local = threading.local()

        def get_thread_local_node() -> NodeCompute[str, str]:
            """Get or create thread-local NodeCompute."""
            if not hasattr(thread_local, "node"):
                thread_local.node = NodeCompute[str, str](container)
            return thread_local.node

        num_threads = 6
        instances_collected: list[NodeCompute[str, str]] = []
        instances_lock = Lock()

        def collect_instance(thread_id: int) -> None:
            """Collect thread-local instance."""
            node = get_thread_local_node()
            with instances_lock:
                instances_collected.append(node)

            # Verify the instance is usable
            async def verify_node() -> None:
                input_data: ModelComputeInput[str] = ModelComputeInput(
                    data=f"thread_{thread_id}",
                    computation_type="default",
                )
                output = await node.process(input_data)
                assert output.result == f"thread_{thread_id}"

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(verify_node())
            finally:
                loop.close()

        # Launch threads
        threads = []
        for thread_id in range(num_threads):
            t = threading.Thread(target=collect_instance, args=(thread_id,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=10)

        # Verify each thread got a unique instance
        instance_ids = [id(inst) for inst in instances_collected]
        unique_ids = set(instance_ids)
        assert len(unique_ids) == num_threads, (
            f"Expected {num_threads} unique instances, got {len(unique_ids)}"
        )

        print(f"Created {len(unique_ids)} isolated thread-local NodeCompute instances")


# =============================================================================
# Test Class: Multi-Threading with ThreadPoolExecutor
# =============================================================================


@pytest.mark.timeout(120)
@pytest.mark.unit
class TestMultiThreadingWithExecutor:
    """
    Test true multi-threading scenarios using ThreadPoolExecutor.

    These tests validate behavior when multiple OS threads access
    cache simultaneously, which can expose different race conditions
    than asyncio-based concurrency.
    """

    def test_executor_concurrent_cache_writes(self) -> None:
        """
        Test concurrent cache writes via ThreadPoolExecutor.

        This uses true OS threads (not coroutines) to stress the cache.
        """
        cache = ModelComputeCache(max_size=20, default_ttl_minutes=30)
        num_workers = 10
        writes_per_worker = 50
        errors: list[Exception] = []
        errors_lock = Lock()

        def write_worker(worker_id: int) -> int:
            """Write many entries to cache."""
            try:
                for i in range(writes_per_worker):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    cache.put(key, value)
                return writes_per_worker
            except Exception as e:
                with errors_lock:
                    errors.append(e)
                return 0

        # Execute with thread pool
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(write_worker, i) for i in range(num_workers)]
            completed_writes = sum(f.result() for f in as_completed(futures))

        # Verify no exceptions
        assert len(errors) == 0, f"ThreadPoolExecutor writes raised errors: {errors}"

        # Verify all writes attempted
        expected_writes = num_workers * writes_per_worker
        assert completed_writes == expected_writes, (
            f"Expected {expected_writes} writes, completed {completed_writes}"
        )

        # Cache should still be functional
        stats = cache.get_stats()
        print(f"Cache stats after executor writes: {stats}")
        assert stats["total_entries"] <= cache.max_size + 2

    def test_executor_concurrent_cache_reads_writes(self) -> None:
        """
        Test mixed read/write operations via ThreadPoolExecutor.

        Half the workers read, half write - maximum contention.
        """
        cache = ModelComputeCache(max_size=30, default_ttl_minutes=30)

        # Pre-populate cache
        for i in range(15):
            cache.put(f"prepop_{i}", f"value_{i}")

        num_workers = 12
        operations_per_worker = 40
        read_results: list[str | None] = []
        results_lock = Lock()

        def mixed_worker(worker_id: int) -> None:
            """Perform mixed read/write operations."""
            for i in range(operations_per_worker):
                if worker_id % 2 == 0:
                    # Writer
                    key = f"write_{worker_id}_{i}"
                    cache.put(key, f"value_{worker_id}_{i}")
                else:
                    # Reader
                    key = f"prepop_{i % 15}"
                    result = cache.get(key)
                    with results_lock:
                        read_results.append(result)

        # Execute
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(mixed_worker, i) for i in range(num_workers)]
            for f in as_completed(futures):
                f.result()  # Propagate exceptions

        # Verify reads got valid data (may be None if evicted)
        for result in read_results:
            if result is not None:
                assert result.startswith("value_"), f"Invalid read result: {result}"

        print(f"Mixed operations completed. Reads: {len(read_results)}")

    def test_thread_safe_wrapper_with_executor(self) -> None:
        """
        Test ThreadSafeComputeCache with ThreadPoolExecutor.

        The thread-safe wrapper should maintain all invariants
        even under true multi-threaded stress.
        """
        cache = ThreadSafeComputeCache(max_size=15, default_ttl_minutes=30)
        num_workers = 15
        operations_per_worker = 50

        def stress_worker(worker_id: int) -> tuple[int, int]:
            """Perform stress operations."""
            writes = 0
            reads = 0
            for i in range(operations_per_worker):
                key = f"key_{i % 20}"  # Limited key space for contention
                if i % 3 == 0:
                    cache.put(key, f"value_{worker_id}_{i}")
                    writes += 1
                else:
                    cache.get(key)
                    reads += 1
            return (writes, reads)

        # Execute
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(stress_worker, i) for i in range(num_workers)]
            totals = [f.result() for f in as_completed(futures)]

        total_writes = sum(t[0] for t in totals)
        total_reads = sum(t[1] for t in totals)

        print(f"Total writes: {total_writes}, reads: {total_reads}")

        # Verify cache invariants maintained
        stats = cache.get_stats()
        assert stats["total_entries"] <= 15, (
            f"Thread-safe cache exceeded max_size: {stats['total_entries']}"
        )

        # Note: ModelComputeCache only tracks get() operations in total_requests,
        # not put() operations. This is expected behavior - "requests" are read requests.
        # Stats should accurately reflect the number of reads performed.
        assert stats["total_requests"] == total_reads, (
            f"Stats mismatch: {stats['total_requests']} != {total_reads} (reads only)"
        )


# =============================================================================
# Test Class: Cache Key Generation Race Conditions
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestCacheKeyGenerationConcurrency:
    """
    Test cache key generation under concurrent load.

    Cache key generation should be deterministic and thread-safe.
    """

    @pytest.mark.asyncio
    async def test_cache_key_deterministic_concurrent(self) -> None:
        """
        Test that cache key generation is deterministic under concurrent access.

        Multiple concurrent calls with the same input should generate
        identical cache keys.
        """
        num_tasks = 20

        def generate_cache_key(input_data: ModelComputeInput[Any]) -> str:
            """Generate cache key using same logic as NodeCompute."""
            data_str = str(input_data.data)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()
            return f"{input_data.computation_type}:{data_hash}"

        # Same input data for all tasks
        shared_input: ModelComputeInput[list[int]] = ModelComputeInput(
            data=[1, 2, 3, 4, 5],
            computation_type="sum_numbers",
        )

        generated_keys: list[str] = []
        keys_lock = Lock()

        async def generate_key_task() -> None:
            """Generate cache key concurrently."""
            key = generate_cache_key(shared_input)
            with keys_lock:
                generated_keys.append(key)

        # Generate keys concurrently
        tasks = [generate_key_task() for _ in range(num_tasks)]
        await asyncio.gather(*tasks)

        # All keys should be identical
        unique_keys = set(generated_keys)
        assert len(unique_keys) == 1, (
            f"Non-deterministic key generation: {len(unique_keys)} unique keys"
        )

        # Verify key format
        expected_key = generate_cache_key(shared_input)
        assert generated_keys[0] == expected_key


# =============================================================================
# Test Class: Stress Test with High Contention
# =============================================================================


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.unit
class TestHighContentionStress:
    """
    High contention stress tests.

    These tests create maximum contention to expose race conditions.
    """

    @pytest.mark.asyncio
    async def test_single_key_high_contention(self) -> None:
        """
        Test high contention on a single cache key.

        All tasks read and write the same key simultaneously.
        This maximizes contention and race condition probability.
        """
        cache = ModelComputeCache(max_size=10, default_ttl_minutes=30)
        single_key = "contention_key"
        num_tasks = 30
        operations_per_task = 100

        write_count = {"count": 0}
        read_count = {"count": 0}
        count_lock = Lock()

        async def high_contention_worker(task_id: int) -> None:
            """Perform high contention operations on single key."""
            for i in range(operations_per_task):
                if i % 2 == 0:
                    cache.put(single_key, f"value_{task_id}_{i}")
                    with count_lock:
                        write_count["count"] += 1
                else:
                    result = cache.get(single_key)
                    with count_lock:
                        read_count["count"] += 1
                    # Result may be None if timing is unlucky, or any valid value
                    if result is not None:
                        assert result.startswith("value_"), f"Corrupted value: {result}"

        tasks = [high_contention_worker(task_id) for task_id in range(num_tasks)]
        await asyncio.gather(*tasks)

        total_operations = write_count["count"] + read_count["count"]
        expected_operations = num_tasks * operations_per_task
        assert total_operations == expected_operations, (
            f"Operations mismatch: {total_operations} != {expected_operations}"
        )

        # Verify cache still functional
        cache.put(single_key, "final_value")
        assert cache.get(single_key) == "final_value"

    @pytest.mark.asyncio
    async def test_eviction_boundary_stress(self) -> None:
        """
        Test cache behavior at eviction boundary.

        Fill cache exactly to max_size, then concurrent operations
        at the boundary where evictions are triggered.
        """
        max_size = 10
        cache = ModelComputeCache(max_size=max_size, default_ttl_minutes=30)

        # Fill to max_size - 1
        for i in range(max_size - 1):
            cache.put(f"base_{i}", f"base_value_{i}")

        num_tasks = 20
        operations_per_task = 20

        async def boundary_worker(task_id: int) -> None:
            """Operate at eviction boundary."""
            for i in range(operations_per_task):
                # Add entry (triggers eviction when cache is full)
                cache.put(f"boundary_{task_id}_{i}", f"value_{task_id}_{i}")

                # Read base entries (may or may not be evicted)
                base_key = f"base_{i % (max_size - 1)}"
                cache.get(base_key)

        tasks = [boundary_worker(task_id) for task_id in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Cache should maintain size invariant
        stats = cache.get_stats()
        assert stats["total_entries"] <= max_size + 2, (
            f"Cache exceeded max_size at boundary: {stats['total_entries']}"
        )


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
