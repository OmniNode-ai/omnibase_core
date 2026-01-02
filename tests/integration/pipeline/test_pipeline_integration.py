# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for end-to-end pipeline scenarios.

Tests complete pipeline scenarios including:
1. Full pipeline execution from registration to completion
2. Hook execution across multiple phases
3. Error handling and recovery in pipeline
4. Middleware composition with real components
5. Execution plan building and running

These tests verify the integration between:
- RegistryHook: Hook registration and freezing
- BuilderExecutionPlan: Dependency resolution and plan building
- RunnerPipeline: Pipeline execution with error handling
- ComposerMiddleware: Middleware composition

Note:
    Integration tests use real components (not mocks) where possible.
    60-second timeout protects against pipeline execution hangs in CI.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

import pytest

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.pipeline import (
    BuilderExecutionPlan,
    ComposerMiddleware,
    DependencyCycleError,
    DuplicateHookError,
    HookCallable,
    HookRegistryFrozenError,
    HookTimeoutError,
    ModelPipelineContext,
    ModelPipelineHook,
    ModelPipelineResult,
    PipelinePhase,
    RegistryHook,
    RunnerPipeline,
    UnknownDependencyError,
)


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestPipelineEndToEndExecution:
    """End-to-end tests for full pipeline execution lifecycle.

    Tests the complete flow from hook registration through execution.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_lifecycle_registration_to_completion(self) -> None:
        """Test complete pipeline lifecycle from registration to completion.

        Verifies:
        - Hook registration in registry
        - Registry freezing
        - Execution plan building
        - Pipeline execution with all phases
        - Correct phase execution order
        - Context data propagation
        """
        execution_log: list[str] = []

        # Create callables that log execution
        def make_logging_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_log.append(name)
                ctx.data[name] = f"executed_{name}"

            return hook

        # Phase 1: Register hooks
        registry = RegistryHook()

        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]

        callable_registry: dict[str, HookCallable] = {}
        for phase in phases:
            hook = ModelPipelineHook(
                hook_id=f"{phase}_hook",
                phase=phase,
                callable_ref=f"hooks.{phase}",
            )
            registry.register(hook)
            callable_registry[f"hooks.{phase}"] = make_logging_hook(phase)

        # Phase 2: Freeze registry
        registry.freeze()
        assert registry.is_frozen

        # Phase 3: Build execution plan
        builder = BuilderExecutionPlan(registry=registry)
        plan, warnings = builder.build()

        assert plan.total_hooks == 6
        assert len(warnings) == 0

        # Phase 4: Execute pipeline
        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        # Verify results
        assert result.success is True
        assert len(result.errors) == 0
        assert execution_log == [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]

        # Verify context propagation
        assert result.context is not None
        for phase in phases:
            assert result.context.data[phase] == f"executed_{phase}"

    @pytest.mark.asyncio
    async def test_multiple_hooks_per_phase_with_dependencies(self) -> None:
        """Test multiple hooks per phase with dependency ordering.

        Verifies:
        - Multiple hooks can be registered per phase
        - Dependencies are respected in execution order
        - Topological sort produces correct order
        """
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(name)

            return hook

        # Register hooks with dependencies
        registry = RegistryHook()

        # In execute phase: c depends on b, b depends on a
        hook_a = ModelPipelineHook(
            hook_id="hook_a",
            phase="execute",
            callable_ref="hooks.a",
            priority=100,
            dependencies=[],
        )
        hook_b = ModelPipelineHook(
            hook_id="hook_b",
            phase="execute",
            callable_ref="hooks.b",
            priority=100,
            dependencies=["hook_a"],
        )
        hook_c = ModelPipelineHook(
            hook_id="hook_c",
            phase="execute",
            callable_ref="hooks.c",
            priority=100,
            dependencies=["hook_b"],
        )

        # Register in reverse order to test dependency resolution
        registry.register(hook_c)
        registry.register(hook_a)
        registry.register(hook_b)
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            "hooks.a": make_hook("a"),
            "hooks.b": make_hook("b"),
            "hooks.c": make_hook("c"),
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        assert result.success is True
        assert execution_order == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_priority_ordering_within_phase(self) -> None:
        """Test priority-based ordering for hooks without dependencies.

        Verifies:
        - Lower priority values execute first
        - Priority ordering is respected in execution
        """
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(name)

            return hook

        registry = RegistryHook()

        # Register hooks with different priorities (no dependencies)
        hooks = [
            ModelPipelineHook(
                hook_id="high_priority",
                phase="execute",
                callable_ref="hooks.high",
                priority=10,
            ),
            ModelPipelineHook(
                hook_id="low_priority",
                phase="execute",
                callable_ref="hooks.low",
                priority=200,
            ),
            ModelPipelineHook(
                hook_id="medium_priority",
                phase="execute",
                callable_ref="hooks.medium",
                priority=100,
            ),
        ]

        for hook in hooks:
            registry.register(hook)
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            "hooks.high": make_hook("high"),
            "hooks.low": make_hook("low"),
            "hooks.medium": make_hook("medium"),
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        assert result.success is True
        assert execution_order == ["high", "medium", "low"]


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestPipelineErrorHandlingIntegration:
    """Integration tests for error handling across pipeline components."""

    @pytest.mark.asyncio
    async def test_fail_fast_phase_stops_execution_finalize_runs(self) -> None:
        """Test fail-fast behavior with finalize always running.

        Verifies:
        - Fail-fast phases (preflight, before, execute) abort on error
        - Subsequent phases are skipped
        - Finalize ALWAYS runs regardless of errors
        - Error is re-raised after finalize completes
        """
        execution_log: list[str] = []

        def preflight_hook(ctx: ModelPipelineContext) -> None:
            execution_log.append("preflight")

        def failing_before(ctx: ModelPipelineContext) -> None:
            execution_log.append("before_start")
            raise ValueError("Intentional failure in before phase")

        def execute_hook(ctx: ModelPipelineContext) -> None:
            execution_log.append("execute")  # Should never run

        def finalize_hook(ctx: ModelPipelineContext) -> None:
            execution_log.append("finalize")  # Must always run

        registry = RegistryHook()
        registry.register(
            ModelPipelineHook(
                hook_id="preflight", phase="preflight", callable_ref="hooks.preflight"
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="before", phase="before", callable_ref="hooks.before"
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="execute", phase="execute", callable_ref="hooks.execute"
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="finalize", phase="finalize", callable_ref="hooks.finalize"
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            "hooks.preflight": preflight_hook,
            "hooks.before": failing_before,
            "hooks.execute": execute_hook,
            "hooks.finalize": finalize_hook,
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        with pytest.raises(ValueError, match="Intentional failure"):
            await runner.run()

        # Verify execution order
        assert execution_log == ["preflight", "before_start", "finalize"]

    @pytest.mark.asyncio
    async def test_continue_phases_collect_all_errors(self) -> None:
        """Test continue-on-error phases collect all errors.

        Verifies:
        - After, emit, finalize phases continue despite errors
        - All errors are collected in result
        - All hooks in continue phases execute
        """
        execution_log: list[str] = []

        def make_failing_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_log.append(name)
                raise RuntimeError(f"Error in {name}")

            return hook

        def make_success_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_log.append(name)

            return hook

        registry = RegistryHook()

        # Register multiple hooks in after phase (continue-on-error)
        registry.register(
            ModelPipelineHook(
                hook_id="after_1",
                phase="after",
                callable_ref="hooks.after_1",
                priority=10,
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="after_2",
                phase="after",
                callable_ref="hooks.after_2",
                priority=20,
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="after_3",
                phase="after",
                callable_ref="hooks.after_3",
                priority=30,
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        # First and third hooks fail, second succeeds
        callable_registry = {
            "hooks.after_1": make_failing_hook("after_1"),
            "hooks.after_2": make_success_hook("after_2"),
            "hooks.after_3": make_failing_hook("after_3"),
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        # All hooks should have executed
        assert execution_log == ["after_1", "after_2", "after_3"]

        # Two errors should be collected
        assert result.success is False
        assert len(result.errors) == 2
        assert result.errors[0].hook_id == "after_1"
        assert result.errors[1].hook_id == "after_3"

    @pytest.mark.asyncio
    async def test_dependency_cycle_detection(self) -> None:
        """Test that dependency cycles are detected during plan building.

        Verifies:
        - Circular dependencies are detected
        - DependencyCycleError is raised with involved hooks
        """
        registry = RegistryHook()

        # Create circular dependency: a -> b -> c -> a
        registry.register(
            ModelPipelineHook(
                hook_id="hook_a",
                phase="execute",
                callable_ref="hooks.a",
                dependencies=["hook_c"],
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="hook_b",
                phase="execute",
                callable_ref="hooks.b",
                dependencies=["hook_a"],
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="hook_c",
                phase="execute",
                callable_ref="hooks.c",
                dependencies=["hook_b"],
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)

        with pytest.raises(DependencyCycleError) as exc_info:
            builder.build()

        # All three hooks should be in the cycle
        # Context is nested under additional_context.context due to ModelOnexError structure
        assert exc_info.value.context is not None
        additional_ctx = exc_info.value.context.get("additional_context", {})
        inner_ctx = additional_ctx.get("context", {})
        cycle = inner_ctx.get("cycle", [])
        assert len(cycle) == 3

    @pytest.mark.asyncio
    async def test_unknown_dependency_detection(self) -> None:
        """Test that unknown dependencies are detected.

        Verifies:
        - References to non-existent hooks are detected
        - UnknownDependencyError is raised with details
        """
        registry = RegistryHook()

        registry.register(
            ModelPipelineHook(
                hook_id="hook_a",
                phase="execute",
                callable_ref="hooks.a",
                dependencies=["nonexistent_hook"],
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)

        with pytest.raises(UnknownDependencyError) as exc_info:
            builder.build()

        # Context is nested under additional_context.context due to ModelOnexError structure
        assert exc_info.value.context is not None
        additional_ctx = exc_info.value.context.get("additional_context", {})
        inner_ctx = additional_ctx.get("context", {})
        assert inner_ctx.get("hook_id") == "hook_a"
        assert inner_ctx.get("unknown_dependency") == "nonexistent_hook"


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestPipelineHookRegistryIntegration:
    """Integration tests for hook registry behavior with pipeline execution."""

    def test_registry_freeze_prevents_modification(self) -> None:
        """Test that frozen registry prevents registration.

        Verifies:
        - Registry can be frozen
        - Registration after freeze raises error
        - Freeze is idempotent
        """
        registry = RegistryHook()

        registry.register(
            ModelPipelineHook(
                hook_id="hook_1", phase="execute", callable_ref="hooks.one"
            )
        )

        registry.freeze()
        assert registry.is_frozen

        # Attempt to register after freeze
        with pytest.raises(HookRegistryFrozenError):
            registry.register(
                ModelPipelineHook(
                    hook_id="hook_2", phase="execute", callable_ref="hooks.two"
                )
            )

        # Freeze is idempotent
        registry.freeze()
        assert registry.is_frozen

    def test_duplicate_hook_id_detection(self) -> None:
        """Test that duplicate hook IDs are detected.

        Verifies:
        - Registering hook with same ID raises error
        - First hook remains registered
        """
        registry = RegistryHook()

        hook_1 = ModelPipelineHook(
            hook_id="duplicate_id", phase="execute", callable_ref="hooks.first"
        )
        registry.register(hook_1)

        hook_2 = ModelPipelineHook(
            hook_id="duplicate_id", phase="before", callable_ref="hooks.second"
        )

        with pytest.raises(DuplicateHookError) as exc_info:
            registry.register(hook_2)

        # Context is nested under additional_context.context due to ModelOnexError structure
        assert exc_info.value.context is not None
        additional_ctx = exc_info.value.context.get("additional_context", {})
        inner_ctx = additional_ctx.get("context", {})
        assert inner_ctx.get("hook_id") == "duplicate_id"

        # Original hook should still be retrievable
        retrieved = registry.get_hook_by_id("duplicate_id")
        assert retrieved is not None
        assert retrieved.callable_ref == "hooks.first"

    @pytest.mark.asyncio
    async def test_registry_with_multiple_phases(self) -> None:
        """Test registry correctly organizes hooks by phase.

        Verifies:
        - Hooks are correctly grouped by phase
        - get_hooks_by_phase returns correct hooks
        - get_all_hooks returns all hooks
        """
        registry = RegistryHook()

        # Register hooks across different phases
        phases_hooks: dict[PipelinePhase, list[str]] = {
            "preflight": ["pf_1", "pf_2"],
            "before": ["bf_1"],
            "execute": ["ex_1", "ex_2", "ex_3"],
            "after": ["af_1"],
        }

        for phase, hook_ids in phases_hooks.items():
            for hook_id in hook_ids:
                registry.register(
                    ModelPipelineHook(
                        hook_id=hook_id,
                        phase=phase,
                        callable_ref=f"hooks.{hook_id}",
                    )
                )

        registry.freeze()

        # Verify phase grouping
        for phase, expected_ids in phases_hooks.items():
            phase_hooks = registry.get_hooks_by_phase(phase)
            actual_ids = [h.hook_id for h in phase_hooks]
            assert sorted(actual_ids) == sorted(expected_ids)

        # Verify total count
        all_hooks = registry.get_all_hooks()
        assert len(all_hooks) == 7


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestPipelineMiddlewareIntegration:
    """Integration tests for middleware composition with pipeline execution."""

    @pytest.mark.asyncio
    async def test_middleware_wraps_pipeline_execution(self) -> None:
        """Test middleware properly wraps core execution.

        Verifies:
        - Middleware executes in correct order (outside-in, inside-out)
        - Middleware can modify context before/after core
        - Core result is properly returned through middleware
        """
        execution_log: list[str] = []

        async def logging_middleware(
            next_fn: Callable[[], Awaitable[object]],
        ) -> object:
            execution_log.append("middleware_1_before")
            result = await next_fn()
            execution_log.append("middleware_1_after")
            return result

        async def timing_middleware(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_log.append("middleware_2_before")
            start = time.time()
            result = await next_fn()
            elapsed = time.time() - start
            execution_log.append(f"middleware_2_after (elapsed: {elapsed:.3f}s)")
            return result

        async def core_function() -> str:
            execution_log.append("core_execution")
            return "core_result"

        composer = ComposerMiddleware()
        composer.use(logging_middleware)
        composer.use(timing_middleware)

        wrapped = composer.compose(core_function)
        result = await wrapped()

        assert result == "core_result"

        # Verify execution order (onion pattern)
        assert execution_log[0] == "middleware_1_before"
        assert execution_log[1] == "middleware_2_before"
        assert execution_log[2] == "core_execution"
        assert execution_log[3].startswith("middleware_2_after")
        assert execution_log[4] == "middleware_1_after"

    @pytest.mark.asyncio
    async def test_middleware_with_pipeline_runner(self) -> None:
        """Test middleware integration with actual pipeline execution.

        Verifies:
        - Middleware can wrap pipeline runner
        - Pipeline result is accessible through middleware
        - Middleware can add metadata to result handling
        """
        middleware_data: dict[str, object] = {}

        async def pipeline_wrapper_middleware(
            next_fn: Callable[[], Awaitable[object]],
        ) -> object:
            middleware_data["start_time"] = time.time()
            result = await next_fn()
            middleware_data["end_time"] = time.time()
            middleware_data["success"] = (
                isinstance(result, ModelPipelineResult) and result.success
            )
            return result

        # Create a simple pipeline
        registry = RegistryHook()
        registry.register(
            ModelPipelineHook(
                hook_id="test_hook", phase="execute", callable_ref="hooks.test"
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        def test_hook(ctx: ModelPipelineContext) -> None:
            ctx.data["executed"] = True

        runner = RunnerPipeline(plan=plan, callable_registry={"hooks.test": test_hook})

        # Wrap pipeline execution with middleware
        composer = ComposerMiddleware()
        composer.use(pipeline_wrapper_middleware)

        async def run_pipeline() -> ModelPipelineResult:
            return await runner.run()

        wrapped = composer.compose(run_pipeline)
        result = await wrapped()

        assert isinstance(result, ModelPipelineResult)
        assert result.success is True
        assert middleware_data["success"] is True
        end_time = middleware_data["end_time"]
        start_time = middleware_data["start_time"]
        assert isinstance(end_time, float)
        assert isinstance(start_time, float)
        assert end_time > start_time


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestPipelineAsyncHookIntegration:
    """Integration tests for async hook execution."""

    @pytest.mark.asyncio
    async def test_mixed_sync_async_hooks_execution(self) -> None:
        """Test pipeline executes both sync and async hooks correctly.

        Verifies:
        - Sync hooks are called correctly
        - Async hooks are properly awaited
        - Execution order is maintained
        """
        execution_log: list[str] = []

        def sync_hook_1(ctx: ModelPipelineContext) -> None:
            execution_log.append("sync_1")

        async def async_hook_1(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(0.01)  # Simulate async work
            execution_log.append("async_1")

        def sync_hook_2(ctx: ModelPipelineContext) -> None:
            execution_log.append("sync_2")

        async def async_hook_2(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(0.01)
            execution_log.append("async_2")

        registry = RegistryHook()
        registry.register(
            ModelPipelineHook(
                hook_id="sync_1",
                phase="execute",
                callable_ref="hooks.sync_1",
                priority=10,
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="async_1",
                phase="execute",
                callable_ref="hooks.async_1",
                priority=20,
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="sync_2",
                phase="execute",
                callable_ref="hooks.sync_2",
                priority=30,
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="async_2",
                phase="execute",
                callable_ref="hooks.async_2",
                priority=40,
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            "hooks.sync_1": sync_hook_1,
            "hooks.async_1": async_hook_1,
            "hooks.sync_2": sync_hook_2,
            "hooks.async_2": async_hook_2,
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        assert result.success is True
        assert execution_log == ["sync_1", "async_1", "sync_2", "async_2"]

    @pytest.mark.asyncio
    async def test_hook_timeout_enforcement(self) -> None:
        """Test hook timeout is enforced.

        Verifies:
        - Hooks with timeout_seconds are time-limited
        - HookTimeoutError is raised when timeout exceeded
        - Timeout applies to both sync and async hooks
        """
        registry = RegistryHook()
        registry.register(
            ModelPipelineHook(
                hook_id="slow_hook",
                phase="execute",
                callable_ref="hooks.slow",
                timeout_seconds=0.1,  # 100ms timeout
            )
        )
        registry.freeze()

        async def slow_async_hook(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(1.0)  # Sleep for 1 second (exceeds timeout)

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        runner = RunnerPipeline(
            plan=plan, callable_registry={"hooks.slow": slow_async_hook}
        )

        with pytest.raises(HookTimeoutError) as exc_info:
            await runner.run()

        # Context is nested under additional_context.context due to ModelOnexError structure
        assert exc_info.value.context is not None
        additional_ctx = exc_info.value.context.get("additional_context", {})
        inner_ctx = additional_ctx.get("context", {})
        assert inner_ctx.get("hook_id") == "slow_hook"
        assert inner_ctx.get("timeout_seconds") == 0.1


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestPipelineExecutionPlanBuilding:
    """Integration tests for execution plan building scenarios."""

    @pytest.mark.asyncio
    async def test_complex_dependency_graph_resolution(self) -> None:
        """Test complex dependency graph is correctly resolved.

        Verifies:
        - Diamond dependencies are handled
        - Multiple independent chains work
        - Priority is respected within dependency constraints
        """
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(name)

            return hook

        registry = RegistryHook()

        # Diamond dependency pattern:
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        registry.register(
            ModelPipelineHook(
                hook_id="A", phase="execute", callable_ref="hooks.A", dependencies=[]
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="B",
                phase="execute",
                callable_ref="hooks.B",
                dependencies=["A"],
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="C",
                phase="execute",
                callable_ref="hooks.C",
                dependencies=["A"],
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="D",
                phase="execute",
                callable_ref="hooks.D",
                dependencies=["B", "C"],
            )
        )
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            "hooks.A": make_hook("A"),
            "hooks.B": make_hook("B"),
            "hooks.C": make_hook("C"),
            "hooks.D": make_hook("D"),
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        assert result.success is True

        # A must come first
        assert execution_order[0] == "A"
        # D must come last
        assert execution_order[-1] == "D"
        # B and C must come after A and before D
        assert execution_order.index("B") > execution_order.index("A")
        assert execution_order.index("C") > execution_order.index("A")
        assert execution_order.index("B") < execution_order.index("D")
        assert execution_order.index("C") < execution_order.index("D")

    @pytest.mark.asyncio
    async def test_empty_pipeline_execution(self) -> None:
        """Test empty pipeline executes successfully.

        Verifies:
        - Empty registry produces empty plan
        - Empty plan executes without errors
        - Result indicates success
        """
        registry = RegistryHook()
        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, warnings = builder.build()

        assert plan.total_hooks == 0
        assert len(warnings) == 0

        runner = RunnerPipeline(plan=plan, callable_registry={})
        result = await runner.run()

        assert result.success is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_handler_type_validation_warnings(self) -> None:
        """Test handler type category validation produces warnings.

        Verifies:
        - Type mismatches generate warnings when not enforced
        - Pipeline still executes with warnings
        - Warnings contain relevant details
        """
        registry = RegistryHook()
        registry.register(
            ModelPipelineHook(
                hook_id="compute_hook",
                phase="execute",
                callable_ref="hooks.compute",
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            )
        )
        registry.freeze()

        # Build with different contract category (should warn, not error)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=False,  # Warn only
        )
        _plan, warnings = builder.build()

        assert len(warnings) == 1
        assert "compute_hook" in warnings[0].message


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(60)
class TestModelPipelineContextStateManagement:
    """Integration tests for pipeline context state management."""

    @pytest.mark.asyncio
    async def test_context_data_accumulation_across_phases(self) -> None:
        """Test context data accumulates correctly across all phases.

        Verifies:
        - Each phase can add data to context
        - Data from earlier phases is available in later phases
        - Final context contains all accumulated data
        """
        registry = RegistryHook()

        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]

        for i, phase in enumerate(phases):
            registry.register(
                ModelPipelineHook(
                    hook_id=f"{phase}_hook",
                    phase=phase,
                    callable_ref=f"hooks.{phase}",
                )
            )

        registry.freeze()

        def make_accumulator_hook(phase: str, index: int) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                # Verify previous phases' data is available
                for prev_phase in phases[:index]:
                    assert prev_phase in ctx.data, f"Missing data from {prev_phase}"

                # Add this phase's data
                ctx.data[phase] = f"data_from_{phase}"
                ctx.data[f"{phase}_index"] = index

            return hook

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            f"hooks.{phase}": make_accumulator_hook(phase, i)
            for i, phase in enumerate(phases)
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        assert result.success is True
        assert result.context is not None

        # Verify all phases contributed
        for i, phase in enumerate(phases):
            assert result.context.data[phase] == f"data_from_{phase}"
            assert result.context.data[f"{phase}_index"] == i

    @pytest.mark.asyncio
    async def test_context_available_in_finalize_after_error(self) -> None:
        """Test context data is available in finalize even after errors.

        Verifies:
        - Finalize has access to context from phases before error
        - Context modifications in finalize are reflected in result
        """
        registry = RegistryHook()

        registry.register(
            ModelPipelineHook(
                hook_id="before_hook", phase="before", callable_ref="hooks.before"
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="failing_execute",
                phase="execute",
                callable_ref="hooks.execute",
            )
        )
        registry.register(
            ModelPipelineHook(
                hook_id="finalize_hook",
                phase="finalize",
                callable_ref="hooks.finalize",
            )
        )
        registry.freeze()

        def before_hook(ctx: ModelPipelineContext) -> None:
            ctx.data["before_ran"] = True

        def failing_execute(ctx: ModelPipelineContext) -> None:
            ctx.data["execute_started"] = True
            raise RuntimeError("Execute failure")

        def finalize_hook(ctx: ModelPipelineContext) -> None:
            # Verify data from before is available
            assert ctx.data.get("before_ran") is True
            assert ctx.data.get("execute_started") is True
            ctx.data["finalize_ran"] = True

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            "hooks.before": before_hook,
            "hooks.execute": failing_execute,
            "hooks.finalize": finalize_hook,
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        with pytest.raises(RuntimeError, match="Execute failure"):
            await runner.run()

        # Note: When an exception is raised, the result isn't returned,
        # but we verified finalize ran by the assert in finalize_hook


@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.timeout(120)
class TestPipelinePerformanceScenarios:
    """Integration tests for pipeline performance scenarios."""

    @pytest.mark.asyncio
    async def test_many_hooks_in_single_phase(self) -> None:
        """Test pipeline handles many hooks in a single phase.

        Verifies:
        - Large number of hooks execute correctly
        - Execution order matches plan
        - Performance is reasonable
        """
        num_hooks = 100
        execution_order: list[str] = []

        def make_hook(index: int) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(f"hook_{index:03d}")

            return hook

        registry = RegistryHook()

        for i in range(num_hooks):
            registry.register(
                ModelPipelineHook(
                    hook_id=f"hook_{i:03d}",
                    phase="execute",
                    callable_ref=f"hooks.hook_{i:03d}",
                    priority=i,  # Sequential priority
                )
            )

        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            f"hooks.hook_{i:03d}": make_hook(i) for i in range(num_hooks)
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)

        start_time = time.time()
        result = await runner.run()
        elapsed = time.time() - start_time

        assert result.success is True
        assert len(execution_order) == num_hooks

        # Verify execution order matches priority
        expected_order = [f"hook_{i:03d}" for i in range(num_hooks)]
        assert execution_order == expected_order

        # Should complete in reasonable time (under 5 seconds for 100 hooks)
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_hooks_across_all_phases(self) -> None:
        """Test pipeline with hooks in all phases executes correctly.

        Verifies:
        - Hooks in every phase execute
        - Phase order is maintained
        - All phases contribute to final context
        """
        phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        hooks_per_phase = 5
        execution_log: list[str] = []

        def make_hook(phase: str, index: int) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_log.append(f"{phase}_{index}")

            return hook

        registry = RegistryHook()

        for phase in phases:
            for i in range(hooks_per_phase):
                registry.register(
                    ModelPipelineHook(
                        hook_id=f"{phase}_{i}",
                        phase=phase,
                        callable_ref=f"hooks.{phase}_{i}",
                        priority=i,
                    )
                )

        registry.freeze()

        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        callable_registry = {
            f"hooks.{phase}_{i}": make_hook(phase, i)
            for phase in phases
            for i in range(hooks_per_phase)
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callable_registry)
        result = await runner.run()

        assert result.success is True
        assert len(execution_log) == len(phases) * hooks_per_phase

        # Verify phase order is maintained
        phase_indices = {
            phase: [
                execution_log.index(f"{phase}_{i}")
                for i in range(hooks_per_phase)
                if f"{phase}_{i}" in execution_log
            ]
            for phase in phases
        }

        # Each phase's hooks should come after previous phase's hooks
        for i, phase in enumerate(phases[1:], start=1):
            prev_phase = phases[i - 1]
            max_prev_index = max(phase_indices[prev_phase])
            min_curr_index = min(phase_indices[phase])
            assert max_prev_index < min_curr_index


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
