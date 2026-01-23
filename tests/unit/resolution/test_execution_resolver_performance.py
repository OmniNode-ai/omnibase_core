# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Performance tests for ExecutionResolver.

Tests validate that the ExecutionResolver maintains acceptable algorithmic
complexity at scale, particularly:
    - O(1) dictionary lookups for constraint resolution
    - O(V + E) topological sort complexity
    - Deterministic tie-breaking performance

Performance Thresholds:
    - All tests should complete in under 1 second
    - Linear scaling is acceptable (not exponential)
    - No significant degradation with constraint density

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ExecutionResolver: The resolver implementation
    - test_execution_resolver.py: Functional tests

.. versionadded:: 0.4.1
"""

import time
from typing import Any

import pytest

from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)
from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.resolution import ExecutionResolver

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def resolver() -> ExecutionResolver:
    """Create a fresh ExecutionResolver instance."""
    return ExecutionResolver()


@pytest.fixture
def default_profile() -> ModelExecutionProfile:
    """Create a default execution profile with priority and alphabetical tie-breakers."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["priority", "alphabetical"],
            deterministic_seed=True,
        ),
    )


@pytest.fixture
def alphabetical_only_profile() -> ModelExecutionProfile:
    """Create a profile with only alphabetical tie-breaking."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["alphabetical"],
            deterministic_seed=True,
        ),
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _create_contract(
    handler_id: str,
    *,
    requires_before: list[str] | None = None,
    requires_after: list[str] | None = None,
    must_run: bool = False,
    tags: list[str] | None = None,
    capability_outputs: list[str] | None = None,
    priority: int = 0,
    metadata: dict[str, Any] | None = None,
) -> ModelHandlerContract:
    """Helper to create a handler contract for testing.

    Args:
        handler_id: Unique identifier for the handler.
        requires_before: List of constraint references this handler requires to run before.
        requires_after: List of constraint references that must run after this handler.
        must_run: Whether this handler must run even if no consumers need its output.
        tags: List of tags for this handler.
        capability_outputs: List of capabilities this handler provides.
        priority: Priority level (lower = higher priority).
        metadata: Additional metadata to include.

    Returns:
        ModelHandlerContract configured with the specified parameters.
    """
    constraints = None
    if requires_before or requires_after or must_run:
        constraints = ModelExecutionConstraints(
            requires_before=requires_before or [],
            requires_after=requires_after or [],
            must_run=must_run,
        )

    final_metadata: dict[str, Any] = {"priority": priority}
    if metadata:
        final_metadata.update(metadata)

    return ModelHandlerContract(
        handler_id=handler_id,
        name=f"Handler {handler_id}",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        descriptor=ModelHandlerBehavior(node_archetype="compute"),
        input_model="test.Input",
        output_model="test.Output",
        execution_constraints=constraints,
        tags=tags or [],
        capability_outputs=capability_outputs or [],
        metadata=final_metadata,
    )


# =============================================================================
# Performance Test Suite
# =============================================================================


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestExecutionResolverPerformance:
    """Performance test suite for ExecutionResolver at scale.

    Tests verify that resolution maintains acceptable performance with:
        - Large numbers of handlers (100-200)
        - High constraint density (500+ constraints)
        - Long dependency chains (worst-case for topological sort)
        - Tie-breaking stress (all handlers at same priority)

    Performance Thresholds:
        All tests should complete resolution in under 1 second.
        This provides margin for CI environments with variable performance.

    Threshold Rationale:
        - Dictionary lookups for constraint resolution: O(1)
        - Topological sort (Kahn's algorithm): O(V + E)
        - Tie-breaking comparison: O(n log n) within each level
        - Total expected time for 200 handlers, 500 constraints: <100ms
        - 1 second threshold provides 10x margin for CI reliability
    """

    def test_baseline_100_handlers_minimal_constraints(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Baseline test: 100 handlers with minimal constraints.

        Establishes baseline performance for comparison with stress tests.
        Uses ~10% constraint density (10 constraints across 100 handlers).

        Performance Threshold:
            - Resolution completes in < 1 second
            - Provides baseline for comparing high-constraint scenarios
        """
        num_handlers = 100
        contracts: list[ModelHandlerContract] = []

        # Create 100 handlers with sparse dependencies
        # Only every 10th handler has a dependency on the previous
        for i in range(num_handlers):
            handler_id = f"handler.perf{i:03d}"

            if i > 0 and i % 10 == 0:
                # Every 10th handler depends on the previous
                contracts.append(
                    _create_contract(
                        handler_id,
                        requires_before=[f"handler:handler.perf{i - 1:03d}"],
                        priority=i,
                    )
                )
            else:
                contracts.append(
                    _create_contract(
                        handler_id,
                        priority=i,
                    )
                )

        # Measure resolution time
        start = time.perf_counter()
        plan = resolver.resolve(default_profile, contracts)
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # Assertions
        assert plan.is_valid, f"Plan should be valid, got conflicts: {plan.conflicts}"
        assert plan.total_handlers() == num_handlers
        assert duration < 1.0, (
            f"Baseline resolution took {duration:.3f}s ({duration_ms:.1f}ms), "
            f"expected <1s for {num_handlers} handlers"
        )

        # Log performance metrics
        print(
            f"\n[BASELINE] {num_handlers} handlers, ~10 constraints: "
            f"{duration_ms:.2f}ms"
        )
        assert plan.resolution_metadata is not None
        print(
            f"  Constraints evaluated: {plan.resolution_metadata.total_constraints_evaluated}"
        )

    def test_stress_100_handlers_500_constraints(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Stress test: 100 handlers with ~500 constraints.

        Tests O(1) dictionary lookup performance for constraint resolution
        under high constraint density (~5 constraints per handler).

        Scenario:
            - 100 handlers, each providing a unique capability
            - Each handler requires 5 capabilities from other handlers
            - Total constraints: ~500 (100 handlers * 5 constraints each)

        Performance Threshold:
            - Resolution completes in < 1 second
            - Demonstrates O(1) constraint lookup at scale
        """
        num_handlers = 100
        constraints_per_handler = 5
        contracts: list[ModelHandlerContract] = []

        # Create handlers with capabilities
        for i in range(num_handlers):
            handler_id = f"handler.stress{i:03d}"
            capability = f"capability.cap{i:03d}"

            # Each handler depends on 5 previous handlers' capabilities
            # (wrapping around to create more complex graph)
            requires = []
            for offset in range(1, constraints_per_handler + 1):
                dep_idx = (i - offset) % num_handlers
                if dep_idx != i:  # No self-dependency
                    requires.append(f"capability:capability.cap{dep_idx:03d}")

            contracts.append(
                _create_contract(
                    handler_id,
                    capability_outputs=[capability],
                    requires_before=requires if requires else None,
                    priority=i,
                )
            )

        # Measure resolution time
        start = time.perf_counter()
        plan = resolver.resolve(default_profile, contracts)
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # Note: This may create cycles due to circular dependencies
        # The test validates performance even with conflict detection
        if plan.is_valid:
            assert plan.total_handlers() == num_handlers
        else:
            # Cycle detection should still be fast
            assert len(plan.conflicts) > 0

        assert duration < 1.0, (
            f"Stress resolution took {duration:.3f}s ({duration_ms:.1f}ms), "
            f"expected <1s for {num_handlers} handlers with ~{num_handlers * constraints_per_handler} constraints"
        )

        # Log performance metrics
        print(
            f"\n[STRESS] {num_handlers} handlers, ~{num_handlers * constraints_per_handler} constraints: "
            f"{duration_ms:.2f}ms"
        )
        if plan.resolution_metadata:
            print(
                f"  Constraints evaluated: {plan.resolution_metadata.total_constraints_evaluated}"
            )
        print(f"  Plan valid: {plan.is_valid}")

    def test_stress_100_handlers_500_constraints_linear_chain(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Stress test: 100 handlers with 500 constraints in valid linear structure.

        Unlike the previous test, this creates a valid DAG to test
        resolution performance without cycle detection overhead.

        Scenario:
            - 100 handlers arranged in groups of 20
            - Each group's handlers depend on all handlers from previous group
            - Creates ~500 constraints in a valid DAG

        Performance Threshold:
            - Resolution completes in < 1 second
        """
        num_handlers = 100
        group_size = 20
        contracts: list[ModelHandlerContract] = []

        for i in range(num_handlers):
            handler_id = f"handler.linear{i:03d}"
            group = i // group_size

            # Handlers in first group have no dependencies
            if group == 0:
                contracts.append(
                    _create_contract(
                        handler_id,
                        capability_outputs=[f"cap.linear{i:03d}"],
                        priority=i,
                    )
                )
            else:
                # Each handler depends on all handlers from the previous group
                prev_group_start = (group - 1) * group_size
                requires = [
                    f"handler:handler.linear{j:03d}"
                    for j in range(prev_group_start, prev_group_start + group_size)
                ]
                contracts.append(
                    _create_contract(
                        handler_id,
                        capability_outputs=[f"cap.linear{i:03d}"],
                        requires_before=requires,
                        priority=i,
                    )
                )

        # Measure resolution time
        start = time.perf_counter()
        plan = resolver.resolve(default_profile, contracts)
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # This should produce a valid plan
        assert plan.is_valid, f"Plan should be valid, got conflicts: {plan.conflicts}"
        assert plan.total_handlers() == num_handlers

        assert duration < 1.0, (
            f"Linear chain resolution took {duration:.3f}s ({duration_ms:.1f}ms), "
            f"expected <1s for {num_handlers} handlers"
        )

        # Verify ordering is correct (groups should be in order)
        handlers = plan.get_all_handler_ids()
        for i in range(1, num_handlers):
            current_group = int(handlers[i].split("linear")[1]) // group_size
            prev_group = int(handlers[i - 1].split("linear")[1]) // group_size
            assert current_group >= prev_group, (
                f"Handler {handlers[i]} (group {current_group}) should not appear "
                f"before handler {handlers[i - 1]} (group {prev_group})"
            )

        # Log performance metrics
        total_constraints = (num_handlers - group_size) * group_size
        print(
            f"\n[LINEAR STRESS] {num_handlers} handlers, ~{total_constraints} constraints: "
            f"{duration_ms:.2f}ms"
        )
        if plan.resolution_metadata:
            print(
                f"  Constraints evaluated: {plan.resolution_metadata.total_constraints_evaluated}"
            )

    def test_worst_case_200_handler_chain(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Worst case test: 200 handlers in a single dependency chain.

        Tests worst-case performance for topological sort where all
        handlers are in a strict linear order (no parallelism possible).

        Scenario:
            - h0 -> h1 -> h2 -> ... -> h199
            - Each handler depends on exactly one previous handler
            - Topological sort must process all 200 nodes sequentially

        Performance Threshold:
            - Resolution completes in < 1 second
            - Validates O(V + E) complexity of Kahn's algorithm
        """
        num_handlers = 200
        contracts: list[ModelHandlerContract] = []

        # Create the chain: each handler depends on the previous
        contracts.append(_create_contract("handler.chain000", priority=0))
        for i in range(1, num_handlers):
            contracts.append(
                _create_contract(
                    f"handler.chain{i:03d}",
                    requires_before=[f"handler:handler.chain{i - 1:03d}"],
                    priority=i,
                )
            )

        # Measure resolution time
        start = time.perf_counter()
        plan = resolver.resolve(default_profile, contracts)
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # Assertions
        assert plan.is_valid, f"Plan should be valid, got conflicts: {plan.conflicts}"
        assert plan.total_handlers() == num_handlers

        assert duration < 1.0, (
            f"Chain resolution took {duration:.3f}s ({duration_ms:.1f}ms), "
            f"expected <1s for {num_handlers}-handler chain"
        )

        # Verify ordering is strictly sequential
        handlers = plan.get_all_handler_ids()
        for i in range(num_handlers):
            expected = f"handler.chain{i:03d}"
            assert handlers[i] == expected, (
                f"Expected {expected} at position {i}, got {handlers[i]}"
            )

        # Log performance metrics
        print(f"\n[CHAIN] {num_handlers} handlers in chain: {duration_ms:.2f}ms")
        if plan.resolution_metadata:
            print(
                f"  Constraints evaluated: {plan.resolution_metadata.total_constraints_evaluated}"
            )

    def test_tie_breaker_stress_same_priority(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Tie-breaker stress test: All handlers at same priority level.

        Tests tie-breaker performance when all handlers have equal priority,
        forcing alphabetical fallback for every ordering decision.

        Scenario:
            - 100 handlers, all with priority=0
            - No dependencies between handlers
            - Every handler comparison requires tie-breaking

        Performance Threshold:
            - Resolution completes in < 1 second
            - Tie-breaking is O(n log n) for each batch of ready handlers
        """
        num_handlers = 100
        contracts: list[ModelHandlerContract] = []

        # Create handlers with shuffled names to stress alphabetical sorting
        # Use a pattern that creates many similar prefixes
        for i in range(num_handlers):
            # Create handler IDs that require careful alphabetical comparison
            suffix_a = chr(ord("a") + (i % 26))
            suffix_b = chr(ord("a") + ((i // 26) % 26))
            handler_id = f"handler.tie.{suffix_b}{suffix_a}{i:02d}"

            contracts.append(
                _create_contract(
                    handler_id,
                    priority=0,  # All same priority
                )
            )

        # Measure resolution time
        start = time.perf_counter()
        plan = resolver.resolve(alphabetical_only_profile, contracts)
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # Assertions
        assert plan.is_valid, f"Plan should be valid, got conflicts: {plan.conflicts}"
        assert plan.total_handlers() == num_handlers

        assert duration < 1.0, (
            f"Tie-breaker resolution took {duration:.3f}s ({duration_ms:.1f}ms), "
            f"expected <1s for {num_handlers} handlers with same priority"
        )

        # Verify output is alphabetically sorted
        handlers = plan.get_all_handler_ids()
        assert handlers == sorted(handlers), (
            "Handlers should be alphabetically sorted when all have same priority"
        )

        # Log performance metrics
        print(
            f"\n[TIE-BREAKER] {num_handlers} handlers at same priority: "
            f"{duration_ms:.2f}ms"
        )
        if plan.resolution_metadata:
            print(
                f"  Tie-breaker decisions: {len(plan.resolution_metadata.tie_breaker_decisions)}"
            )

    def test_mixed_constraints_capability_tag_handler(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Mixed constraint types: capability, tag, and handler references.

        Tests index lookup performance when using all three constraint
        reference types (capability:, tag:, handler:).

        Scenario:
            - 50 handlers with capabilities
            - 50 handlers with tags
            - Constraints reference all three types

        Performance Threshold:
            - Resolution completes in < 1 second
            - All index types use O(1) dictionary lookups
        """
        num_handlers = 100
        contracts: list[ModelHandlerContract] = []

        # First half: handlers with capabilities
        for i in range(num_handlers // 2):
            contracts.append(
                _create_contract(
                    f"handler.cap{i:03d}",
                    capability_outputs=[f"cap.{i:03d}"],
                    tags=[f"group.{i % 5}"],  # 5 tag groups
                    priority=i,
                )
            )

        # Second half: handlers with mixed dependencies
        for i in range(num_handlers // 2, num_handlers):
            offset = i - (num_handlers // 2)
            requires = [
                f"capability:cap.{offset:03d}",  # Capability reference
                f"tag:group.{offset % 5}",  # Tag reference
            ]
            if offset > 0:
                requires.append(f"handler:handler.cap{offset - 1:03d}")  # Handler ref

            contracts.append(
                _create_contract(
                    f"handler.dep{i:03d}",
                    requires_before=requires,
                    priority=i,
                )
            )

        # Measure resolution time
        start = time.perf_counter()
        plan = resolver.resolve(default_profile, contracts)
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # Assertions
        assert plan.is_valid, f"Plan should be valid, got conflicts: {plan.conflicts}"
        assert plan.total_handlers() == num_handlers

        assert duration < 1.0, (
            f"Mixed constraint resolution took {duration:.3f}s ({duration_ms:.1f}ms), "
            f"expected <1s for {num_handlers} handlers with mixed constraint types"
        )

        # Verify capability handlers come before dependent handlers
        handlers = plan.get_all_handler_ids()
        for i in range(num_handlers // 2, num_handlers):
            offset = i - (num_handlers // 2)
            cap_handler = f"handler.cap{offset:03d}"
            dep_handler = f"handler.dep{i:03d}"
            if cap_handler in handlers and dep_handler in handlers:
                assert handlers.index(cap_handler) < handlers.index(dep_handler), (
                    f"{cap_handler} should come before {dep_handler}"
                )

        # Log performance metrics
        print(
            f"\n[MIXED] {num_handlers} handlers with mixed constraint types: "
            f"{duration_ms:.2f}ms"
        )
        if plan.resolution_metadata:
            print(
                f"  Constraints evaluated: {plan.resolution_metadata.total_constraints_evaluated}"
            )


@pytest.mark.performance
@pytest.mark.unit
class TestExecutionResolverDeterminismPerformance:
    """Tests verifying deterministic performance across multiple runs.

    Validates that:
        - Same inputs produce same timing characteristics
        - No significant variance between runs
        - Deterministic seed produces consistent results
    """

    def test_repeated_resolution_consistency(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that repeated resolutions have consistent performance.

        Runs the same resolution multiple times and verifies:
            - All runs produce identical results
            - Performance variance is within acceptable bounds

        Performance Threshold:
            - Standard deviation of run times < 50% of mean
            - Demonstrates consistent algorithmic complexity
        """
        num_handlers = 50
        num_iterations = 10
        contracts: list[ModelHandlerContract] = []

        # Create a fixed set of contracts
        for i in range(num_handlers):
            if i > 0 and i % 5 == 0:
                contracts.append(
                    _create_contract(
                        f"handler.repeat{i:03d}",
                        requires_before=[f"handler:handler.repeat{i - 1:03d}"],
                        priority=i,
                    )
                )
            else:
                contracts.append(_create_contract(f"handler.repeat{i:03d}", priority=i))

        # Run multiple iterations
        durations: list[float] = []
        results: list[list[str]] = []

        for _ in range(num_iterations):
            start = time.perf_counter()
            plan = resolver.resolve(default_profile, contracts)
            duration = time.perf_counter() - start

            durations.append(duration)
            results.append(plan.get_all_handler_ids())

            assert plan.is_valid

        # Verify all results are identical
        for i in range(1, num_iterations):
            assert results[i] == results[0], (
                f"Run {i} produced different results than run 0"
            )

        # Calculate statistics
        mean_duration = sum(durations) / len(durations)
        variance = sum((d - mean_duration) ** 2 for d in durations) / len(durations)
        std_dev = variance**0.5

        # Verify performance consistency
        # Allow for some variance due to system load
        assert std_dev < mean_duration * 0.5, (
            f"High variance in resolution times: mean={mean_duration * 1000:.2f}ms, "
            f"std_dev={std_dev * 1000:.2f}ms"
        )

        # Log performance metrics
        print(
            f"\n[CONSISTENCY] {num_iterations} runs of {num_handlers} handlers: "
            f"mean={mean_duration * 1000:.2f}ms, std_dev={std_dev * 1000:.2f}ms"
        )
        print(
            f"  Min: {min(durations) * 1000:.2f}ms, Max: {max(durations) * 1000:.2f}ms"
        )
