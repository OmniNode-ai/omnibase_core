# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Performance benchmarks for RegistryHook with large hook counts.

This module tests hook registry and pipeline runner scalability,
measuring registration throughput, lookup latency, phase execution
performance, and memory usage patterns.

Performance Requirements (PR #291):
- Registry with 100+ hooks: <10ms registration
- Registry with 1000+ hooks: <100ms registration
- Hook lookup: <0.1ms average
- Phase execution: scales linearly with hook count
"""

import time
from collections.abc import Callable

import pytest

from omnibase_core.models.pipeline import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineHook,
    PipelinePhase,
)
from omnibase_core.pipeline.registry_hook import RegistryHook
from omnibase_core.pipeline.runner_pipeline import (
    HookCallable,
    PipelineContext,
    RunnerPipeline,
)

# ===== Test Fixture Factories =====


def create_test_hook(
    hook_name: str,
    phase: PipelinePhase = "execute",
    priority: int = 100,
    dependencies: list[str] | None = None,
) -> ModelPipelineHook:
    """Create a test hook with minimal boilerplate.

    Args:
        hook_name: Unique identifier for the hook
        phase: Pipeline phase for the hook
        priority: Execution priority (lower = earlier)
        dependencies: List of hook names that must run first

    Returns:
        ModelPipelineHook instance
    """
    return ModelPipelineHook(
        hook_name=hook_name,
        phase=phase,
        callable_ref=f"test.{hook_name}",
        priority=priority,
        dependencies=dependencies or [],
    )


def create_noop_callable() -> HookCallable:
    """Create a minimal no-op callable for performance testing.

    Returns:
        A callable that does nothing (minimal overhead)
    """

    def noop(ctx: PipelineContext) -> None:
        pass

    return noop


def make_plan_with_hooks(
    *phase_hooks: tuple[PipelinePhase, list[ModelPipelineHook]],
) -> ModelExecutionPlan:
    """Helper to create an execution plan with hooks.

    Args:
        *phase_hooks: Tuples of (phase, hooks_list)

    Returns:
        ModelExecutionPlan with the specified hooks
    """
    phases: dict[PipelinePhase, ModelPhaseExecutionPlan] = {}
    for phase, hooks in phase_hooks:
        fail_fast = phase in ("preflight", "before", "execute")
        phases[phase] = ModelPhaseExecutionPlan(
            phase=phase,
            hooks=hooks,
            fail_fast=fail_fast,
        )
    return ModelExecutionPlan(phases=phases)


# ===== Hook Registration Performance Tests =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestRegistryHookRegistrationPerformance:
    """Performance tests for hook registration scalability.

    Tests registration throughput and latency at various scales
    to ensure the registry can handle production workloads.
    """

    def test_register_100_hooks(self) -> None:
        """Test registering 100 hooks.

        Performance Threshold:
        - Total registration time < 10ms
        - Average registration time < 0.1ms per hook

        Threshold Rationale:
            - Dict insertion is O(1), ~1us per operation
            - Hook validation adds ~10-50us overhead
            - 10ms threshold provides 100x margin for CI variance
        """
        num_hooks = 100
        registry = RegistryHook()

        start_time = time.perf_counter()

        for i in range(num_hooks):
            hook = create_test_hook(f"hook-{i:04d}", phase="execute")
            registry.register(hook)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_us = (total_time_ms / num_hooks) * 1000

        # Verify all hooks registered
        assert len(registry.get_all_hooks()) == num_hooks

        # Verify performance threshold
        assert total_time_ms < 10.0, (
            f"Total registration time {total_time_ms:.3f}ms exceeds 10ms threshold"
        )

        print(
            f"\n[OK] Registered {num_hooks} hooks in {total_time_ms:.3f}ms "
            f"(avg: {avg_time_us:.1f}us per hook)"
        )

    def test_register_1000_hooks(self) -> None:
        """Test registering 1000 hooks.

        Performance Threshold:
        - Total registration time < 100ms
        - Average registration time < 0.1ms per hook

        This is the primary scalability test for the hook registry.
        """
        num_hooks = 1000
        registry = RegistryHook()

        start_time = time.perf_counter()

        for i in range(num_hooks):
            hook = create_test_hook(f"hook-{i:04d}", phase="execute")
            registry.register(hook)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_us = (total_time_ms / num_hooks) * 1000

        # Verify all hooks registered
        assert len(registry.get_all_hooks()) == num_hooks

        # Verify performance threshold
        assert total_time_ms < 100.0, (
            f"Total registration time {total_time_ms:.3f}ms exceeds 100ms threshold"
        )
        assert avg_time_us < 100.0, (
            f"Average registration time {avg_time_us:.1f}us exceeds 100us threshold"
        )

        print(
            f"\n[OK] Registered {num_hooks} hooks in {total_time_ms:.3f}ms "
            f"(avg: {avg_time_us:.1f}us per hook)"
        )

    def test_register_hooks_across_all_phases(self) -> None:
        """Test registering hooks across all 6 phases.

        Validates that phase partitioning doesn't impact performance.

        Performance Threshold:
        - 1000 hooks (166+ per phase) in < 100ms
        """
        num_hooks_per_phase = 166
        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        registry = RegistryHook()

        start_time = time.perf_counter()

        for phase in phases:
            for i in range(num_hooks_per_phase):
                hook = create_test_hook(f"{phase}-hook-{i:04d}", phase=phase)
                registry.register(hook)

        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        total_hooks = num_hooks_per_phase * len(phases)

        # Verify all hooks registered
        assert len(registry.get_all_hooks()) == total_hooks

        # Verify hooks per phase
        for phase in phases:
            phase_hooks = registry.get_hooks_by_phase(phase)
            assert len(phase_hooks) == num_hooks_per_phase

        # Verify performance threshold
        assert total_time_ms < 100.0, (
            f"Total registration time {total_time_ms:.3f}ms exceeds 100ms threshold"
        )

        print(
            f"\n[OK] Registered {total_hooks} hooks across {len(phases)} phases "
            f"in {total_time_ms:.3f}ms"
        )

    def test_registration_throughput(self) -> None:
        """Test registration throughput (operations per second).

        Performance Threshold:
        - Throughput > 5,000 registrations/second

        Note: Threshold lowered from 10,000 to 5,000 to accommodate
        containerized CI environments with variable performance.
        """
        num_hooks = 1000
        registry = RegistryHook()

        start_time = time.perf_counter()

        for i in range(num_hooks):
            hook = create_test_hook(f"throughput-hook-{i:04d}")
            registry.register(hook)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = num_hooks / total_time

        # Verify throughput threshold (5,000 ops/s is CI-friendly)
        assert throughput > 5000.0, (
            f"Throughput {throughput:.1f} ops/s below 5,000 ops/s threshold"
        )

        print(
            f"\n[OK] Registration throughput: {throughput:.1f} hooks/second "
            f"({num_hooks} hooks in {total_time:.4f}s)"
        )


# ===== Hook Lookup Performance Tests =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestRegistryHookLookupPerformance:
    """Performance tests for hook lookup operations.

    Tests retrieval latency for various lookup patterns to ensure
    fast hook resolution at runtime.
    """

    def test_get_hook_by_name_with_1000_hooks(self) -> None:
        """Test get_hook_by_name performance with 1000 hooks.

        Performance Threshold:
        - Average lookup time < 0.01ms (10us)
        - 1000 lookups complete in < 10ms

        Threshold Rationale:
            - Dict lookup is O(1), typically ~0.5-1us
            - 10us threshold provides margin for CI environments
        """
        num_hooks = 1000
        registry = RegistryHook()

        # Register hooks
        for i in range(num_hooks):
            hook = create_test_hook(f"lookup-hook-{i:04d}")
            registry.register(hook)

        registry.freeze()

        # Measure lookup performance
        num_lookups = 1000
        lookup_times: list[float] = []

        for i in range(num_lookups):
            hook_name = f"lookup-hook-{i % num_hooks:04d}"

            start_time = time.perf_counter()
            result = registry.get_hook_by_name(hook_name)
            end_time = time.perf_counter()

            lookup_time_us = (end_time - start_time) * 1_000_000
            lookup_times.append(lookup_time_us)

            assert result is not None

        avg_lookup_us = sum(lookup_times) / len(lookup_times)
        max_lookup_us = max(lookup_times)
        total_time_ms = sum(lookup_times) / 1000

        # Verify performance thresholds
        assert avg_lookup_us < 10.0, (
            f"Average lookup time {avg_lookup_us:.2f}us exceeds 10us threshold"
        )
        assert total_time_ms < 10.0, (
            f"Total lookup time {total_time_ms:.3f}ms exceeds 10ms threshold"
        )

        print(
            f"\n[OK] Hook lookup with {num_hooks} hooks: "
            f"avg={avg_lookup_us:.2f}us, max={max_lookup_us:.2f}us"
        )

    def test_get_hooks_by_phase_with_large_registry(self) -> None:
        """Test get_hooks_by_phase performance with 1000 hooks.

        Performance Threshold:
        - Phase lookup + copy < 1ms per call
        """
        num_hooks_per_phase = 166
        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        registry = RegistryHook()

        # Register hooks across phases
        for phase in phases:
            for i in range(num_hooks_per_phase):
                hook = create_test_hook(f"{phase}-lookup-{i:04d}", phase=phase)
                registry.register(hook)

        registry.freeze()

        # Measure phase lookup performance
        num_lookups_per_phase = 100
        lookup_times: dict[str, list[float]] = {phase: [] for phase in phases}

        for phase in phases:
            for _ in range(num_lookups_per_phase):
                start_time = time.perf_counter()
                hooks = registry.get_hooks_by_phase(phase)
                end_time = time.perf_counter()

                lookup_time_ms = (end_time - start_time) * 1000
                lookup_times[phase].append(lookup_time_ms)

                assert len(hooks) == num_hooks_per_phase

        # Calculate statistics per phase
        for phase in phases:
            avg_time = sum(lookup_times[phase]) / len(lookup_times[phase])
            max_time = max(lookup_times[phase])

            assert avg_time < 1.0, (
                f"Phase {phase} avg lookup time {avg_time:.3f}ms exceeds 1ms threshold"
            )

            print(f"  {phase}: avg={avg_time:.3f}ms, max={max_time:.3f}ms")

        print(f"\n[OK] Phase lookups verified for {len(phases)} phases")

    def test_get_all_hooks_with_1000_hooks(self) -> None:
        """Test get_all_hooks performance with 1000 hooks.

        Performance Threshold:
        - get_all_hooks completes in < 5ms
        """
        num_hooks = 1000
        registry = RegistryHook()

        # Register hooks
        for i in range(num_hooks):
            hook = create_test_hook(f"all-hooks-{i:04d}")
            registry.register(hook)

        registry.freeze()

        # Measure get_all_hooks performance
        num_calls = 100
        call_times: list[float] = []

        for _ in range(num_calls):
            start_time = time.perf_counter()
            all_hooks = registry.get_all_hooks()
            end_time = time.perf_counter()

            call_time_ms = (end_time - start_time) * 1000
            call_times.append(call_time_ms)

            assert len(all_hooks) == num_hooks

        avg_time_ms = sum(call_times) / len(call_times)
        max_time_ms = max(call_times)

        # Verify performance threshold
        assert avg_time_ms < 5.0, (
            f"Average get_all_hooks time {avg_time_ms:.3f}ms exceeds 5ms threshold"
        )

        print(
            f"\n[OK] get_all_hooks with {num_hooks} hooks: "
            f"avg={avg_time_ms:.3f}ms, max={max_time_ms:.3f}ms"
        )


# ===== Pipeline Execution Performance Tests =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(120)
@pytest.mark.unit
class TestRunnerPipelineExecutionPerformance:
    """Performance tests for pipeline execution with many hooks.

    Tests phase execution latency to ensure the pipeline runner
    scales efficiently with hook count.
    """

    @pytest.mark.asyncio
    async def test_execute_100_hooks_single_phase(self) -> None:
        """Test executing 100 hooks in a single phase.

        Performance Threshold:
        - Total execution time < 50ms (0.5ms per hook)

        Note: This tests pure execution overhead, not hook logic.
        """
        num_hooks = 100
        execution_count = 0

        def counting_callable(ctx: PipelineContext) -> None:
            nonlocal execution_count
            execution_count += 1

        hooks = [
            create_test_hook(f"exec-hook-{i:04d}", phase="execute")
            for i in range(num_hooks)
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        callable_registry: dict[str, HookCallable] = {
            f"test.exec-hook-{i:04d}": counting_callable for i in range(num_hooks)
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        start_time = time.perf_counter()
        result = await runner.run()
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000

        # Verify execution
        assert result.success
        assert execution_count == num_hooks

        # Verify performance threshold
        assert total_time_ms < 50.0, (
            f"Execution time {total_time_ms:.3f}ms exceeds 50ms threshold"
        )

        print(
            f"\n[OK] Executed {num_hooks} hooks in {total_time_ms:.3f}ms "
            f"(avg: {total_time_ms / num_hooks:.3f}ms per hook)"
        )

    @pytest.mark.asyncio
    async def test_execute_1000_hooks_single_phase(self) -> None:
        """Test executing 1000 hooks in a single phase.

        Performance Threshold:
        - Total execution time < 500ms
        - Execution scales linearly with hook count

        This is the primary scalability test for the pipeline runner.
        """
        num_hooks = 1000
        execution_count = 0

        def counting_callable(ctx: PipelineContext) -> None:
            nonlocal execution_count
            execution_count += 1

        hooks = [
            create_test_hook(f"exec-hook-{i:04d}", phase="execute")
            for i in range(num_hooks)
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        callable_registry: dict[str, HookCallable] = {
            f"test.exec-hook-{i:04d}": counting_callable for i in range(num_hooks)
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        start_time = time.perf_counter()
        result = await runner.run()
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000

        # Verify execution
        assert result.success
        assert execution_count == num_hooks

        # Verify performance threshold
        assert total_time_ms < 500.0, (
            f"Execution time {total_time_ms:.3f}ms exceeds 500ms threshold"
        )

        print(
            f"\n[OK] Executed {num_hooks} hooks in {total_time_ms:.3f}ms "
            f"(avg: {total_time_ms / num_hooks:.3f}ms per hook)"
        )

    @pytest.mark.asyncio
    async def test_execute_hooks_across_all_phases(self) -> None:
        """Test executing hooks across all 6 phases.

        Performance Threshold:
        - 1000 total hooks across 6 phases in < 500ms
        """
        num_hooks_per_phase = 166
        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        execution_order: list[str] = []

        def make_tracking_callable(phase: str) -> HookCallable:
            def callable_fn(ctx: PipelineContext) -> None:
                execution_order.append(phase)

            return callable_fn

        hooks_by_phase: list[tuple[PipelinePhase, list[ModelPipelineHook]]] = []
        callable_registry: dict[str, HookCallable] = {}

        for phase in phases:
            hooks = [
                create_test_hook(f"{phase}-exec-{i:04d}", phase=phase)
                for i in range(num_hooks_per_phase)
            ]
            hooks_by_phase.append((phase, hooks))

            for i in range(num_hooks_per_phase):
                callable_registry[f"test.{phase}-exec-{i:04d}"] = (
                    make_tracking_callable(phase)
                )

        plan = make_plan_with_hooks(*hooks_by_phase)
        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        start_time = time.perf_counter()
        result = await runner.run()
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000
        total_hooks = num_hooks_per_phase * len(phases)

        # Verify execution
        assert result.success
        assert len(execution_order) == total_hooks

        # Verify phase ordering
        expected_order = []
        for phase in phases:
            expected_order.extend([phase] * num_hooks_per_phase)
        assert execution_order == expected_order

        # Verify performance threshold
        assert total_time_ms < 500.0, (
            f"Execution time {total_time_ms:.3f}ms exceeds 500ms threshold"
        )

        print(
            f"\n[OK] Executed {total_hooks} hooks across {len(phases)} phases "
            f"in {total_time_ms:.3f}ms"
        )

    @pytest.mark.asyncio
    async def test_async_hooks_execution_performance(self) -> None:
        """Test execution performance with async hooks.

        Performance Threshold:
        - 100 async hooks complete in < 100ms
        """
        num_hooks = 100
        execution_count = 0

        async def async_counting_callable(ctx: PipelineContext) -> None:
            nonlocal execution_count
            execution_count += 1

        hooks = [
            create_test_hook(f"async-hook-{i:04d}", phase="execute")
            for i in range(num_hooks)
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        callable_registry: dict[str, Callable[..., object]] = {
            f"test.async-hook-{i:04d}": async_counting_callable
            for i in range(num_hooks)
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        start_time = time.perf_counter()
        result = await runner.run()
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000

        # Verify execution
        assert result.success
        assert execution_count == num_hooks

        # Verify performance threshold
        assert total_time_ms < 100.0, (
            f"Async execution time {total_time_ms:.3f}ms exceeds 100ms threshold"
        )

        print(f"\n[OK] Executed {num_hooks} async hooks in {total_time_ms:.3f}ms")


# ===== Memory Usage Tests =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestRegistryHookMemoryUsage:
    """Memory usage tests for hook registry with large hook counts.

    Note: These are basic validation tests. Full memory profiling
    would require additional tooling (e.g., memory_profiler, tracemalloc).
    """

    def test_memory_pattern_with_1000_hooks(self) -> None:
        """Test memory usage patterns with 1000 hooks.

        Validates:
        - Registry maintains reasonable memory footprint
        - Data structures scale efficiently
        - Returned lists are copies (thread safety)
        """
        num_hooks = 1000
        registry = RegistryHook()

        # Register hooks
        for i in range(num_hooks):
            hook = create_test_hook(f"memory-hook-{i:04d}")
            registry.register(hook)

        registry.freeze()

        # Verify all hooks registered
        all_hooks = registry.get_all_hooks()
        assert len(all_hooks) == num_hooks

        # Verify copies are returned (thread safety)
        hooks_copy1 = registry.get_all_hooks()
        hooks_copy2 = registry.get_all_hooks()

        # Same content but different list instances
        assert hooks_copy1 == hooks_copy2
        assert hooks_copy1 is not hooks_copy2

        # Modifying copy doesn't affect registry
        hooks_copy1.clear()
        assert len(registry.get_all_hooks()) == num_hooks

        print(f"\n[OK] Memory pattern test: {num_hooks} hooks, copies verified")

    def test_phase_partition_memory_efficiency(self) -> None:
        """Test memory efficiency of phase partitioning.

        Validates that hooks stored by phase don't create duplicate references.
        """
        num_hooks_per_phase = 166
        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        registry = RegistryHook()

        # Register hooks
        for phase in phases:
            for i in range(num_hooks_per_phase):
                hook = create_test_hook(f"{phase}-mem-{i:04d}", phase=phase)
                registry.register(hook)

        registry.freeze()

        total_hooks = num_hooks_per_phase * len(phases)

        # Verify total count
        assert len(registry.get_all_hooks()) == total_hooks

        # Verify per-phase counts
        phase_total = sum(len(registry.get_hooks_by_phase(phase)) for phase in phases)
        assert phase_total == total_hooks

        # Verify no hooks are duplicated between phases
        all_hook_names = {h.hook_name for h in registry.get_all_hooks()}
        assert len(all_hook_names) == total_hooks

        print(
            f"\n[OK] Phase partitioning verified: {total_hooks} hooks, "
            f"{len(phases)} phases, no duplicates"
        )


# ===== Topological Sort Performance Tests =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.unit
class TestTopologicalSortPerformance:
    """Performance tests for topological sort in BuilderExecutionPlan.

    Tests the scalability of the topological sort algorithm (Kahn's algorithm)
    with large numbers of hooks and complex dependency graphs.

    Performance Requirements (PR review feedback):
    - 100 hooks with chain dependencies: < 50ms
    - 1000 hooks with chain dependencies: < 500ms
    - 100+ diamond patterns: < 100ms
    - Linear scaling with hook count
    """

    def test_topological_sort_100_hooks_with_dependencies(self) -> None:
        """Test topological sort with 100 hooks in a dependency chain.

        Performance Threshold:
        - Build time < 50ms

        Dependency Pattern: Linear chain (hook-0001 -> hook-0002 -> ... -> hook-0100)
        This is a worst-case scenario for topological sort as each hook
        must wait for the previous one.
        """
        from omnibase_core.pipeline.builder_execution_plan import BuilderExecutionPlan

        num_hooks = 100
        registry = RegistryHook()

        # Create chain dependencies: hook-0001 -> hook-0002 -> ... -> hook-0100
        for i in range(num_hooks):
            dependencies = [f"hook-{i - 1:04d}"] if i > 0 else []
            hook = create_test_hook(
                f"hook-{i:04d}",
                phase="execute",
                priority=100,
                dependencies=dependencies,
            )
            registry.register(hook)

        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)

        start_time = time.perf_counter()
        plan, _warnings = builder.build()
        end_time = time.perf_counter()

        build_time_ms = (end_time - start_time) * 1000

        # Verify plan was built correctly
        execute_phase = plan.phases.get("execute")
        assert execute_phase is not None
        assert len(execute_phase.hooks) == num_hooks

        # Verify ordering respects dependencies (hook-0000 should come first)
        hook_order = [h.hook_name for h in execute_phase.hooks]
        for i in range(num_hooks):
            assert hook_order[i] == f"hook-{i:04d}", (
                f"Hook at position {i} should be hook-{i:04d}, got {hook_order[i]}"
            )

        # Verify performance threshold
        assert build_time_ms < 50.0, (
            f"Build time {build_time_ms:.3f}ms exceeds 50ms threshold"
        )

        print(
            f"\n[OK] Topological sort with {num_hooks} chained hooks: "
            f"{build_time_ms:.3f}ms"
        )

    def test_topological_sort_1000_hooks_with_dependencies(self) -> None:
        """Test topological sort with 1000 hooks in a dependency chain.

        Performance Threshold:
        - Build time < 500ms

        This tests scalability of Kahn's algorithm with a large chain.
        """
        from omnibase_core.pipeline.builder_execution_plan import BuilderExecutionPlan

        num_hooks = 1000
        registry = RegistryHook()

        # Create chain dependencies
        for i in range(num_hooks):
            dependencies = [f"hook-{i - 1:04d}"] if i > 0 else []
            hook = create_test_hook(
                f"hook-{i:04d}",
                phase="execute",
                priority=100,
                dependencies=dependencies,
            )
            registry.register(hook)

        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)

        start_time = time.perf_counter()
        plan, _warnings = builder.build()
        end_time = time.perf_counter()

        build_time_ms = (end_time - start_time) * 1000

        # Verify plan was built correctly
        execute_phase = plan.phases.get("execute")
        assert execute_phase is not None
        assert len(execute_phase.hooks) == num_hooks

        # Verify first and last hooks are in correct order
        hook_order = [h.hook_name for h in execute_phase.hooks]
        assert hook_order[0] == "hook-0000"
        assert hook_order[-1] == f"hook-{num_hooks - 1:04d}"

        # Verify performance threshold
        assert build_time_ms < 500.0, (
            f"Build time {build_time_ms:.3f}ms exceeds 500ms threshold"
        )

        print(
            f"\n[OK] Topological sort with {num_hooks} chained hooks: "
            f"{build_time_ms:.3f}ms"
        )

    def test_topological_sort_diamond_patterns_at_scale(self) -> None:
        """Test topological sort with 100+ diamond dependency patterns.

        Performance Threshold:
        - Build time < 100ms

        Diamond Pattern:
            A
           / \\
          B   C
           \\ /
            D

        This creates 100 diamond patterns (400 hooks total) to test
        handling of convergent/divergent dependencies.
        """
        from omnibase_core.pipeline.builder_execution_plan import BuilderExecutionPlan

        num_diamonds = 100
        registry = RegistryHook()

        # Create 100 independent diamond patterns
        for d in range(num_diamonds):
            prefix = f"diamond-{d:03d}"

            # A (root) - no dependencies
            hook_a = create_test_hook(
                f"{prefix}-a",
                phase="execute",
                priority=1,
                dependencies=[],
            )
            registry.register(hook_a)

            # B depends on A
            hook_b = create_test_hook(
                f"{prefix}-b",
                phase="execute",
                priority=2,
                dependencies=[f"{prefix}-a"],
            )
            registry.register(hook_b)

            # C depends on A
            hook_c = create_test_hook(
                f"{prefix}-c",
                phase="execute",
                priority=2,
                dependencies=[f"{prefix}-a"],
            )
            registry.register(hook_c)

            # D depends on both B and C
            hook_d = create_test_hook(
                f"{prefix}-d",
                phase="execute",
                priority=3,
                dependencies=[f"{prefix}-b", f"{prefix}-c"],
            )
            registry.register(hook_d)

        registry.freeze()

        total_hooks = num_diamonds * 4
        builder = BuilderExecutionPlan(registry=registry)

        start_time = time.perf_counter()
        plan, _warnings = builder.build()
        end_time = time.perf_counter()

        build_time_ms = (end_time - start_time) * 1000

        # Verify plan was built correctly
        execute_phase = plan.phases.get("execute")
        assert execute_phase is not None
        assert len(execute_phase.hooks) == total_hooks

        # Verify diamond ordering constraints for first diamond
        hook_order = [h.hook_name for h in execute_phase.hooks]
        idx_a = hook_order.index("diamond-000-a")
        idx_b = hook_order.index("diamond-000-b")
        idx_c = hook_order.index("diamond-000-c")
        idx_d = hook_order.index("diamond-000-d")

        # A must come before B and C
        assert idx_a < idx_b, "A must come before B"
        assert idx_a < idx_c, "A must come before C"
        # B and C must come before D
        assert idx_b < idx_d, "B must come before D"
        assert idx_c < idx_d, "C must come before D"

        # Verify performance threshold
        assert build_time_ms < 100.0, (
            f"Build time {build_time_ms:.3f}ms exceeds 100ms threshold"
        )

        print(
            f"\n[OK] Topological sort with {num_diamonds} diamond patterns "
            f"({total_hooks} hooks): {build_time_ms:.3f}ms"
        )

    def test_topological_sort_scales_linearly(self) -> None:
        """Validate topological sort time scales linearly with hook count.

        Tests at 100, 500, 1000 hooks with chain dependencies and validates
        that time increases proportionally.

        Kahn's algorithm is O(V + E), so we expect linear scaling.
        Uses multiple iterations to reduce variance in micro-benchmarks.
        """
        from omnibase_core.pipeline.builder_execution_plan import BuilderExecutionPlan

        scales = [100, 500, 1000]
        num_iterations = 5  # Average multiple iterations to reduce variance
        times: dict[int, float] = {}

        for num_hooks in scales:
            iteration_times: list[float] = []

            for _ in range(num_iterations):
                registry = RegistryHook()

                # Create chain dependencies
                for i in range(num_hooks):
                    dependencies = [f"scale-hook-{i - 1:04d}"] if i > 0 else []
                    hook = create_test_hook(
                        f"scale-hook-{i:04d}",
                        phase="execute",
                        priority=100,
                        dependencies=dependencies,
                    )
                    registry.register(hook)

                registry.freeze()

                builder = BuilderExecutionPlan(registry=registry)

                start_time = time.perf_counter()
                plan, _warnings = builder.build()
                end_time = time.perf_counter()

                iteration_times.append((end_time - start_time) * 1000)

                # Verify plan was built
                execute_phase = plan.phases.get("execute")
                assert execute_phase is not None
                assert len(execute_phase.hooks) == num_hooks

            # Use median to reduce impact of outliers
            iteration_times.sort()
            times[num_hooks] = iteration_times[num_iterations // 2]

        # Validate linear scaling using per-hook time
        # This is more robust than raw ratios for micro-benchmarks
        time_per_hook_100 = times[100] / 100
        time_per_hook_1000 = times[1000] / 1000

        # Per-hook time should be relatively stable (within 5x for micro-benchmarks)
        # Small hook counts have higher overhead per hook, so we check
        # that larger counts don't have significantly HIGHER per-hook time
        assert time_per_hook_1000 < time_per_hook_100 * 5.0, (
            f"Per-hook time increased too much: "
            f"100 hooks: {time_per_hook_100:.4f}ms/hook, "
            f"1000 hooks: {time_per_hook_1000:.4f}ms/hook"
        )

        # Also verify absolute performance is reasonable
        assert times[1000] < 500.0, (
            f"1000 hooks took {times[1000]:.3f}ms, exceeds 500ms threshold"
        )

        print("\n[OK] Topological sort scaling (chain dependencies):")
        for num_hooks, time_ms in times.items():
            per_hook = time_ms / num_hooks
            print(f"  {num_hooks} hooks: {time_ms:.3f}ms ({per_hook:.4f}ms/hook)")
        print(
            f"  Per-hook time ratio 1000/100: {time_per_hook_1000 / time_per_hook_100:.2f}x"
        )

    def test_topological_sort_mixed_dependencies(self) -> None:
        """Test topological sort with mixed dependency patterns.

        Performance Threshold:
        - Build time < 100ms for 500 hooks

        Creates a complex graph with:
        - Some hooks with no dependencies
        - Some hooks with single dependencies
        - Some hooks with multiple dependencies
        - Multiple independent subgraphs
        """
        from omnibase_core.pipeline.builder_execution_plan import BuilderExecutionPlan

        registry = RegistryHook()

        # Create 5 independent subgraphs of 100 hooks each
        num_subgraphs = 5
        hooks_per_subgraph = 100

        for sg in range(num_subgraphs):
            prefix = f"sg-{sg:02d}"

            # First 20 hooks: no dependencies (roots)
            for i in range(20):
                hook = create_test_hook(
                    f"{prefix}-root-{i:02d}",
                    phase="execute",
                    priority=1,
                    dependencies=[],
                )
                registry.register(hook)

            # Next 40 hooks: single dependencies on roots
            for i in range(40):
                root_idx = i % 20
                hook = create_test_hook(
                    f"{prefix}-mid-{i:02d}",
                    phase="execute",
                    priority=2,
                    dependencies=[f"{prefix}-root-{root_idx:02d}"],
                )
                registry.register(hook)

            # Next 40 hooks: multiple dependencies on mid-level
            for i in range(40):
                dep1 = f"{prefix}-mid-{i % 40:02d}"
                dep2 = f"{prefix}-mid-{(i + 1) % 40:02d}"
                hook = create_test_hook(
                    f"{prefix}-leaf-{i:02d}",
                    phase="execute",
                    priority=3,
                    dependencies=[dep1, dep2],
                )
                registry.register(hook)

        registry.freeze()

        total_hooks = num_subgraphs * hooks_per_subgraph
        builder = BuilderExecutionPlan(registry=registry)

        start_time = time.perf_counter()
        plan, _warnings = builder.build()
        end_time = time.perf_counter()

        build_time_ms = (end_time - start_time) * 1000

        # Verify plan was built correctly
        execute_phase = plan.phases.get("execute")
        assert execute_phase is not None
        assert len(execute_phase.hooks) == total_hooks

        # Verify dependency ordering for first subgraph
        hook_order = [h.hook_name for h in execute_phase.hooks]
        root_idx = hook_order.index("sg-00-root-00")
        mid_idx = hook_order.index("sg-00-mid-00")
        leaf_idx = hook_order.index("sg-00-leaf-00")

        assert root_idx < mid_idx, "Root must come before mid"
        assert mid_idx < leaf_idx, "Mid must come before leaf"

        # Verify performance threshold
        assert build_time_ms < 100.0, (
            f"Build time {build_time_ms:.3f}ms exceeds 100ms threshold"
        )

        print(
            f"\n[OK] Topological sort with mixed dependencies "
            f"({total_hooks} hooks, {num_subgraphs} subgraphs): {build_time_ms:.3f}ms"
        )


# ===== Linear Scaling Validation Tests =====


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(120)
@pytest.mark.unit
class TestRegistryHookLinearScaling:
    """Tests to validate linear (O(n)) scaling behavior.

    These tests measure performance at multiple scales to ensure
    operations scale linearly, not quadratically.
    """

    def test_registration_scales_linearly(self) -> None:
        """Validate registration time scales linearly with hook count.

        Tests at 100, 500, 1000 hooks and validates that time
        increases proportionally (within 3x margin for variance).
        """
        scales = [100, 500, 1000]
        times: dict[int, float] = {}

        for num_hooks in scales:
            registry = RegistryHook()

            start_time = time.perf_counter()
            for i in range(num_hooks):
                hook = create_test_hook(f"scale-hook-{i:04d}")
                registry.register(hook)
            end_time = time.perf_counter()

            times[num_hooks] = (end_time - start_time) * 1000

        # Validate linear scaling (time should scale proportionally)
        # Time for 1000 hooks should be roughly 10x time for 100 hooks
        # Allow 3x margin for CI variance
        ratio_500_to_100 = times[500] / times[100]
        ratio_1000_to_100 = times[1000] / times[100]

        # Expected ratios: 5x and 10x, allow up to 3x variance
        assert ratio_500_to_100 < 15.0, (
            f"500/100 ratio {ratio_500_to_100:.1f} suggests non-linear scaling"
        )
        assert ratio_1000_to_100 < 30.0, (
            f"1000/100 ratio {ratio_1000_to_100:.1f} suggests non-linear scaling"
        )

        print("\n[OK] Registration scaling:")
        for num_hooks, time_ms in times.items():
            print(f"  {num_hooks} hooks: {time_ms:.3f}ms")
        print(f"  Ratio 500/100: {ratio_500_to_100:.1f}x")
        print(f"  Ratio 1000/100: {ratio_1000_to_100:.1f}x")

    @pytest.mark.asyncio
    async def test_execution_scales_linearly(self) -> None:
        """Validate execution time scales linearly with hook count.

        Tests at 100, 500, 1000 hooks and validates that execution
        time increases proportionally.
        """
        scales = [100, 500, 1000]
        times: dict[int, float] = {}

        for num_hooks in scales:
            execution_count = 0

            def counting_callable(ctx: PipelineContext) -> None:
                nonlocal execution_count
                execution_count += 1

            hooks = [
                create_test_hook(f"scale-exec-{i:04d}", phase="execute")
                for i in range(num_hooks)
            ]
            plan = make_plan_with_hooks(("execute", hooks))

            callable_registry: dict[str, HookCallable] = {
                f"test.scale-exec-{i:04d}": counting_callable for i in range(num_hooks)
            }

            runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

            start_time = time.perf_counter()
            await runner.run()
            end_time = time.perf_counter()

            times[num_hooks] = (end_time - start_time) * 1000

        # Validate linear scaling
        ratio_500_to_100 = times[500] / times[100]
        ratio_1000_to_100 = times[1000] / times[100]

        # Expected ratios: 5x and 10x, allow up to 3x variance
        assert ratio_500_to_100 < 15.0, (
            f"500/100 ratio {ratio_500_to_100:.1f} suggests non-linear scaling"
        )
        assert ratio_1000_to_100 < 30.0, (
            f"1000/100 ratio {ratio_1000_to_100:.1f} suggests non-linear scaling"
        )

        print("\n[OK] Execution scaling:")
        for num_hooks, time_ms in times.items():
            print(f"  {num_hooks} hooks: {time_ms:.3f}ms")
        print(f"  Ratio 500/100: {ratio_500_to_100:.1f}x")
        print(f"  Ratio 1000/100: {ratio_1000_to_100:.1f}x")
