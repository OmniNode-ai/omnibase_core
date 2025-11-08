"""
Thread Safety Tests for ONEX Node Components.

These tests demonstrate race conditions that can occur without proper
synchronization in multi-threaded environments.

WARNING: Some tests are EXPECTED to fail or show non-deterministic behavior
when run without synchronization. This is intentional to demonstrate the
need for thread-safe wrappers in production.

See docs/THREADING.md for mitigation strategies.
"""

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_effect_types import (
    EnumCircuitBreakerState,
    EnumEffectType,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.configuration.model_circuit_breaker import (
    ModelCircuitBreaker,
)
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache
from omnibase_core.models.model_compute_input import ModelComputeInput
from omnibase_core.models.model_effect_input import ModelEffectInput
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect


class TestCacheRaceConditions:
    """
    Test suite demonstrating cache race conditions.

    These tests may exhibit non-deterministic failures due to concurrent
    access without synchronization. This is EXPECTED behavior to demonstrate
    the need for thread-safe wrappers.
    """

    @pytest.mark.xfail(
        reason="Race demonstration; not a deterministic CI check", strict=False
    )
    def test_cache_concurrent_put_operations(self):
        """
        Demonstrate potential cache corruption with concurrent put operations.

        Expected Behavior WITHOUT Locking:
        - Race conditions may occur in LRU eviction
        - Cache size may exceed max_size temporarily
        - Access counts may be incorrect

        This test may pass sometimes and fail other times - this is the
        nature of race conditions.
        """
        cache = ModelComputeCache(max_size=10, default_ttl_minutes=30)

        def concurrent_writer(thread_id: int, iterations: int):
            """Write many entries concurrently."""
            for i in range(iterations):
                key = f"thread_{thread_id}_key_{i}"
                value = f"value_{thread_id}_{i}"
                cache.put(key, value)

        # Launch multiple threads writing concurrently
        threads = []
        num_threads = 5
        iterations_per_thread = 20

        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=concurrent_writer, args=(thread_id, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Get cache stats
        stats = cache.get_stats()

        # NOTE: Without proper locking, we cannot guarantee cache invariants
        # The cache size SHOULD be <= max_size (10), but races may violate this
        print(f"Cache stats after concurrent writes: {stats}")
        print(f"Total entries: {stats['total_entries']} (max: {cache.max_size})")

        # This assertion may fail without proper synchronization!
        # That's the point - it demonstrates the race condition
        # In production, use ThreadSafeComputeCache wrapper
        assert (
            stats["total_entries"] <= cache.max_size
        ), "Cache exceeded max size due to race condition!"

    @pytest.mark.xfail(
        reason="Demonstrates redundant computations under races", strict=False
    )
    def test_cache_concurrent_get_put_race(self):
        """
        Demonstrate get/put race conditions.

        Race scenario: Thread A checks cache (miss), Thread B writes,
        Thread A writes, resulting in duplicate work or lost updates.
        """
        cache = ModelComputeCache(max_size=100, default_ttl_minutes=30)
        computation_count = {"count": 0}
        lock = threading.Lock()

        def expensive_computation(key: str) -> str:
            """Simulate expensive computation that should be cached."""
            # Track how many times we actually compute
            with lock:
                computation_count["count"] += 1

            # Simulate expensive work
            time.sleep(0.01)
            return f"computed_value_{key}"

        def compute_with_cache(key: str) -> str:
            """Compute with caching - UNSAFE without synchronization."""
            # Check cache
            cached = cache.get(key)
            if cached is not None:
                return cached

            # Cache miss - compute
            result = expensive_computation(key)

            # Store in cache
            cache.put(key, result)
            return result

        # Multiple threads requesting same key concurrently
        # Without locking, they may all miss cache and compute redundantly
        results = []

        def worker(key: str):
            result = compute_with_cache(key)
            results.append(result)

        threads = []
        num_threads = 10
        same_key = "shared_key"

        for _ in range(num_threads):
            thread = threading.Thread(target=worker, args=(same_key,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All results should be identical
        assert all(r == results[0] for r in results), "Inconsistent cached results!"

        # Ideally, computation_count should be 1 (only one actual computation)
        # But without cache locking, multiple threads may compute redundantly
        print(f"Computations performed: {computation_count['count']} (ideal: 1)")

        # This assertion demonstrates the inefficiency of unsafe caching
        # In a perfect world with locking, count would be 1
        # Without locking, we expect > 1 (redundant work)
        # NOTE: This may occasionally pass if race timing is favorable
        if computation_count["count"] > 1:
            print(
                f"⚠️  Race condition detected: {computation_count['count']} redundant computations"
            )

    @pytest.mark.skip(
        reason="Expected to fail without synchronization - demonstrates race condition"
    )
    def test_cache_lru_eviction_race(self):
        """
        Demonstrate LRU eviction race conditions.

        This test is EXPECTED to fail without proper synchronization.
        It demonstrates that concurrent evictions can corrupt cache state.
        """
        cache = ModelComputeCache(max_size=5, default_ttl_minutes=30)

        def concurrent_fill_and_evict(thread_id: int):
            """Fill cache to trigger evictions."""
            for i in range(20):
                key = f"t{thread_id}_k{i}"
                cache.put(key, f"value_{i}")

        threads = []
        for thread_id in range(3):
            thread = threading.Thread(
                target=concurrent_fill_and_evict, args=(thread_id,)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        stats = cache.get_stats()

        # Cache should maintain max_size invariant even under concurrent load
        assert (
            stats["total_entries"] <= cache.max_size
        ), f"Cache corrupted: {stats['total_entries']} entries (max: {cache.max_size})"


class TestCircuitBreakerRaceConditions:
    """
    Test suite demonstrating circuit breaker race conditions.

    Circuit breaker state transitions are not atomic, leading to potential
    failures under concurrent load.
    """

    @pytest.mark.xfail(
        reason="Lost updates under races expected without sync", strict=False
    )
    def test_circuit_breaker_failure_count_race(self):
        """
        Demonstrate failure count race conditions.

        Multiple threads recording failures concurrently may result in
        incorrect failure counts due to non-atomic increments.
        """
        breaker = ModelCircuitBreaker()
        num_threads = 10
        failures_per_thread = 5

        def record_failures():
            """Record multiple failures from one thread."""
            for _ in range(failures_per_thread):
                breaker.record_failure()

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=record_failures)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Expected failure count: num_threads * failures_per_thread
        expected_failures = num_threads * failures_per_thread

        # Actual failure count may be less due to race conditions
        # (lost updates when multiple threads increment concurrently)
        print(f"Expected failures: {expected_failures}")
        print(f"Actual failures: {breaker.failure_count}")

        # This assertion may fail due to lost updates!
        # That's the point - it demonstrates the race condition
        assert (
            breaker.failure_count == expected_failures
        ), f"Lost {expected_failures - breaker.failure_count} failure updates due to race condition"

    @pytest.mark.xfail(
        reason="Unpredictable state transitions under races", strict=False
    )
    def test_circuit_breaker_state_transition_race(self):
        """
        Demonstrate circuit breaker state transition races.

        Concurrent success/failure recordings may cause incorrect state
        transitions (e.g., OPEN -> HALF_OPEN -> CLOSED without proper checks).
        """
        breaker = ModelCircuitBreaker()

        # Trip the breaker
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()

        assert breaker.state == EnumCircuitBreakerState.OPEN, "Breaker should be OPEN"

        # Now concurrent threads try to record successes and failures
        def mixed_operations(success_count: int, failure_count: int):
            """Mix success and failure recordings."""
            for _ in range(success_count):
                breaker.record_success()
            for _ in range(failure_count):
                breaker.record_failure()

        threads = []
        for _ in range(5):
            # Each thread records both successes and failures
            thread = threading.Thread(target=mixed_operations, args=(3, 2))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # State transitions under concurrent load are unpredictable
        # without proper synchronization
        print(f"Final breaker state: {breaker.state}")
        print(f"Final failure count: {breaker.failure_count}")

        # We cannot make reliable assertions about final state
        # due to race conditions - this is the problem we're demonstrating


class TestThreadSafeWrappers:
    """
    Test suite demonstrating CORRECT thread-safe patterns.

    These tests show how to properly synchronize ONEX components for
    production use.
    """

    def test_thread_safe_cache_wrapper(self):
        """
        Demonstrate correct cache synchronization with threading.Lock.

        This is the RECOMMENDED pattern for production use.
        """

        class ThreadSafeComputeCache:
            """Thread-safe wrapper for ModelComputeCache."""

            def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
                self._cache = ModelComputeCache(max_size, default_ttl_minutes)
                self._lock = threading.Lock()

            def get(self, key: str) -> Any | None:
                """Thread-safe get."""
                with self._lock:
                    return self._cache.get(key)

            def put(self, key: str, value: Any, ttl_minutes: int | None = None) -> None:
                """Thread-safe put."""
                with self._lock:
                    self._cache.put(key, value, ttl_minutes)

            def get_stats(self) -> dict[str, int | float]:
                """Thread-safe stats."""
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

        # Use thread-safe wrapper
        cache = ThreadSafeComputeCache(max_size=10)
        computation_count = {"count": 0}
        count_lock = threading.Lock()

        def expensive_computation(key: str) -> str:
            """Track computations."""
            with count_lock:
                computation_count["count"] += 1
            time.sleep(0.01)
            return f"computed_{key}"

        def compute_with_safe_cache(key: str) -> str:
            """Correctly synchronized cache usage with atomic compute_if_absent."""
            return cache.compute_if_absent(key, expensive_computation)

        # Multiple threads requesting same key
        results = []

        def worker(key: str):
            result = compute_with_safe_cache(key)
            results.append(result)

        threads = []
        num_threads = 10
        same_key = "shared_key"

        for _ in range(num_threads):
            thread = threading.Thread(target=worker, args=(same_key,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All results should be identical
        assert all(r == results[0] for r in results), "Inconsistent results!"

        # With proper locking, we still may have some redundant computations
        # due to the check-then-act pattern, but cache state is consistent
        print(f"Computations with thread-safe cache: {computation_count['count']}")
        stats = cache.get_stats()
        print(f"Final cache stats: {stats}")

        # Cache invariants are maintained
        assert stats["total_entries"] <= 10, "Cache size exceeded!"

    def test_thread_local_node_instances(self):
        """
        Demonstrate thread-local node instance pattern.

        This is the RECOMMENDED pattern for concurrent NodeCompute usage.
        """
        container = ModelONEXContainer()
        thread_local = threading.local()

        def get_thread_local_compute() -> NodeCompute:
            """Get or create thread-local NodeCompute instance."""
            if not hasattr(thread_local, "compute_node"):
                thread_local.compute_node = NodeCompute(container)
            return thread_local.compute_node

        # Track which instances were created
        # IMPORTANT: Store actual instances, not just IDs, to prevent GC and memory reuse
        instances = []
        lock = threading.Lock()

        def worker(thread_id: int):
            """Each thread gets its own NodeCompute instance."""
            # Get thread-local instance
            compute_node = get_thread_local_compute()

            # Record the instance (not just ID) to prevent GC while verifying
            with lock:
                instances.append(compute_node)

        # Launch multiple threads, each with its own node instance
        threads = []
        num_threads = 5

        for thread_id in range(num_threads):
            thread = threading.Thread(target=worker, args=(thread_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have gotten a unique instance
        # Check using id() now that all instances are kept alive
        instance_ids = [id(inst) for inst in instances]
        assert len(instance_ids) == num_threads, "All threads should complete"
        assert (
            len(set(instance_ids)) == num_threads
        ), "Each thread should have unique instance"
        print(
            f"Successfully created {len(set(instance_ids))} thread-local NodeCompute instances"
        )


class TestTransactionIsolation:
    """
    Test suite for transaction thread safety.

    Transactions must NEVER be shared across threads.
    """

    def test_transaction_isolation_requirement(self):
        """
        Demonstrate that transactions must be isolated per operation.

        This test shows the CORRECT pattern: one transaction per operation,
        never shared across threads.
        """
        container = ModelONEXContainer()

        async def isolated_effect_operation(operation_id: UUID) -> bool:
            """Each operation gets its own transaction."""
            effect_node = NodeEffect(container)

            # Create transaction for this specific operation
            async with effect_node.transaction_context() as transaction:
                # Transaction is isolated to this context
                # Do NOT share across threads
                return True

        # Multiple threads, each with isolated transactions
        results = []

        def worker(op_id: UUID):
            """Run isolated operation."""
            result = asyncio.run(isolated_effect_operation(op_id))
            results.append(result)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(uuid4(),))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All operations completed with isolated transactions
        assert all(results), "All operations should succeed with isolated transactions"
        print(f"Successfully completed {len(results)} isolated transactions")


class TestDocumentationExamples:
    """
    Test suite validating code examples from docs/THREADING.md.

    These tests ensure documentation examples are correct and functional.
    """

    def test_thread_safe_cache_from_docs(self):
        """Validate ThreadSafeComputeCache example from docs."""
        # This is the exact example from docs/THREADING.md
        from threading import Lock

        class ThreadSafeComputeCache:
            def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
                self._cache = ModelComputeCache(max_size, default_ttl_minutes)
                self._lock = Lock()

            def get(self, key: str) -> Any | None:
                with self._lock:
                    return self._cache.get(key)

            def put(self, key: str, value: Any, ttl_minutes: int | None = None) -> None:
                with self._lock:
                    self._cache.put(key, value, ttl_minutes)

            def clear(self) -> None:
                with self._lock:
                    self._cache.clear()

            def get_stats(self) -> dict[str, int | float]:
                with self._lock:
                    return self._cache.get_stats()

        # Test the documented pattern
        cache = ThreadSafeComputeCache(max_size=100)
        cache.put("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        stats = cache.get_stats()
        assert stats["total_entries"] == 1

    def test_thread_local_pattern_from_docs(self):
        """Validate thread-local pattern from docs."""
        # This is the pattern documented in THREADING.md
        container = ModelONEXContainer()
        thread_local = threading.local()

        def get_compute_node(container):
            if not hasattr(thread_local, "compute_node"):
                thread_local.compute_node = NodeCompute(container)
            return thread_local.compute_node

        # Test that each thread gets its own instance
        # IMPORTANT: Store actual instances, not just IDs, to prevent GC and memory reuse
        instances = []
        lock = threading.Lock()

        def worker():
            time.sleep(0.001)  # Small delay to ensure threads don't overlap
            node = get_compute_node(container)
            with lock:
                instances.append(node)  # Store actual instance, not just ID

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have gotten a different instance
        # Check using id() now that all instances are kept alive
        instance_ids = [id(inst) for inst in instances]
        unique_instances = len(set(instance_ids))
        assert (
            unique_instances == 3
        ), f"Expected 3 unique thread-local instances, got {unique_instances}"


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
