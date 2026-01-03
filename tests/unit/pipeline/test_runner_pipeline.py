# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for RunnerPipeline."""

import pytest

from omnibase_core.models.pipeline import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineContext,
    ModelPipelineHook,
    PipelinePhase,
)
from omnibase_core.pipeline.exceptions import CallableNotFoundError
from omnibase_core.pipeline.runner_pipeline import (
    HookCallable,
    RunnerPipeline,
)


def make_plan_with_hooks(
    *phase_hooks: tuple[PipelinePhase, list[ModelPipelineHook]],
) -> ModelExecutionPlan:
    """Helper to create an execution plan with hooks."""
    phases: dict[PipelinePhase, ModelPhaseExecutionPlan] = {}
    for phase, hooks in phase_hooks:
        fail_fast = phase in ("preflight", "before", "execute")
        phases[phase] = ModelPhaseExecutionPlan(
            phase=phase,
            hooks=hooks,
            fail_fast=fail_fast,
        )
    return ModelExecutionPlan(phases=phases)


@pytest.mark.unit
class TestRunnerPipelinePhaseExecutionOrder:
    """Test hooks execute in canonical phase order."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_phases_execute_in_order(self) -> None:
        """Phases execute in canonical order."""
        execution_order: list[str] = []

        def make_hook_callable(phase_name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(phase_name)

            return hook

        hooks_by_phase: dict[PipelinePhase, list[ModelPipelineHook]] = {}
        for phase in ["preflight", "before", "execute", "after", "emit", "finalize"]:
            hooks_by_phase[phase] = [  # type: ignore[index]
                ModelPipelineHook(
                    hook_id=f"{phase}-hook",
                    phase=phase,  # type: ignore[arg-type]
                    callable_ref=f"test.{phase}",
                )
            ]

        plan = make_plan_with_hooks(*hooks_by_phase.items())  # type: ignore[arg-type]

        # Create callable registry
        callables = {
            f"test.{phase}": make_hook_callable(phase)
            for phase in ["preflight", "before", "execute", "after", "emit", "finalize"]
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callables)
        await runner.run()

        assert execution_order == [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hooks_within_phase_execute_in_plan_order(self) -> None:
        """Hooks within a phase execute in the order from the plan."""
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(name)

            return hook

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="execute", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="execute", callable_ref="test.second"
            ),
            ModelPipelineHook(
                hook_id="third", phase="execute", callable_ref="test.third"
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        callables = {
            "test.first": make_hook("first"),
            "test.second": make_hook("second"),
            "test.third": make_hook("third"),
        }

        runner = RunnerPipeline(plan=plan, callable_registry=callables)
        await runner.run()

        assert execution_order == ["first", "second", "third"]


@pytest.mark.unit
class TestRunnerPipelineFinalizeAlwaysRuns:
    """Test finalize phase ALWAYS runs."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_finalize_runs_on_success(self) -> None:
        """Finalize runs after successful execution."""
        finalize_ran: list[bool] = []

        def finalize_hook(ctx: ModelPipelineContext) -> None:
            finalize_ran.append(True)

        hooks = [
            ModelPipelineHook(
                hook_id="finalize",
                phase="finalize",
                callable_ref="test.finalize",
            )
        ]
        plan = make_plan_with_hooks(("finalize", hooks))

        runner = RunnerPipeline(
            plan=plan, callable_registry={"test.finalize": finalize_hook}
        )
        await runner.run()

        assert finalize_ran == [True]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_finalize_runs_on_exception(self) -> None:
        """Finalize runs even when earlier phase raises exception."""
        finalize_ran: list[bool] = []

        def failing_hook(ctx: ModelPipelineContext) -> None:
            raise ValueError("Intentional failure")

        def finalize_hook_fn(ctx: ModelPipelineContext) -> None:
            finalize_ran.append(True)

        execute_hook = ModelPipelineHook(
            hook_id="failing",
            phase="execute",
            callable_ref="test.failing",
        )
        finalize_hook_model = ModelPipelineHook(
            hook_id="finalize",
            phase="finalize",
            callable_ref="test.finalize",
        )
        plan = make_plan_with_hooks(
            ("execute", [execute_hook]),
            ("finalize", [finalize_hook_model]),
        )

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={
                "test.failing": failing_hook,
                "test.finalize": finalize_hook_fn,
            },
        )

        with pytest.raises(ValueError, match="Intentional failure"):
            await runner.run()

        # Finalize MUST have run despite the exception
        assert finalize_ran == [True]


@pytest.mark.unit
class TestRunnerPipelineErrorHandlingPerPhase:
    """Test error handling behavior per phase."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preflight_fails_fast(self) -> None:
        """Preflight phase aborts on first error."""
        execution_order: list[str] = []

        def first(ctx: ModelPipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Preflight failed")

        def second(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="preflight", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="preflight", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("preflight", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        with pytest.raises(ValueError):
            await runner.run()

        assert execution_order == ["first"]  # Second never ran

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_before_fails_fast(self) -> None:
        """Before phase aborts on first error."""
        execution_order: list[str] = []

        def first(ctx: ModelPipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Before failed")

        def second(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="before", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="before", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("before", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        with pytest.raises(ValueError):
            await runner.run()

        assert execution_order == ["first"]  # Second never ran

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_fails_fast(self) -> None:
        """Execute phase aborts on first error."""
        execution_order: list[str] = []

        def first(ctx: ModelPipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Execute failed")

        def second(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="execute", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="execute", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        with pytest.raises(ValueError):
            await runner.run()

        assert execution_order == ["first"]  # Second never ran

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_after_phase_continues_on_error(self) -> None:
        """After phase continues despite errors."""
        execution_order: list[str] = []

        def first(ctx: ModelPipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("After hook failed")

        def second(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="after", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="after", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("after", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        # Should not raise, continues on error
        result = await runner.run()

        assert execution_order == ["first", "second"]  # Both ran
        assert len(result.errors) > 0  # Error was captured

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_emit_phase_continues_on_error(self) -> None:
        """Emit phase continues despite errors."""
        execution_order: list[str] = []

        def first(ctx: ModelPipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Emit hook failed")

        def second(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(hook_id="first", phase="emit", callable_ref="test.first"),
            ModelPipelineHook(
                hook_id="second", phase="emit", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("emit", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        # Should not raise, continues on error
        result = await runner.run()

        assert execution_order == ["first", "second"]  # Both ran
        assert len(result.errors) > 0  # Error was captured

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_finalize_phase_continues_on_error(self) -> None:
        """Finalize phase continues despite errors."""
        execution_order: list[str] = []

        def first(ctx: ModelPipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Finalize hook failed")

        def second(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="finalize", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="finalize", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("finalize", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        # Should not raise, finalize always continues
        result = await runner.run()

        assert execution_order == ["first", "second"]  # Both ran
        assert len(result.errors) > 0  # Error was captured


@pytest.mark.unit
class TestRunnerPipelineAsyncHookSupport:
    """Test async hook support."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_hook_awaited(self) -> None:
        """Async hooks are properly awaited."""
        execution_order: list[str] = []

        async def async_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("async")

        def sync_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("sync")

        hooks = [
            ModelPipelineHook(
                hook_id="async", phase="execute", callable_ref="test.async"
            ),
            ModelPipelineHook(
                hook_id="sync", phase="execute", callable_ref="test.sync"
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.async": async_hook, "test.sync": sync_hook},
        )
        await runner.run()

        assert execution_order == ["async", "sync"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mixed_sync_async_hooks(self) -> None:
        """Mixed sync and async hooks execute correctly."""
        execution_order: list[str] = []

        def sync_first(ctx: ModelPipelineContext) -> None:
            execution_order.append("sync_first")

        async def async_middle(ctx: ModelPipelineContext) -> None:
            execution_order.append("async_middle")

        def sync_last(ctx: ModelPipelineContext) -> None:
            execution_order.append("sync_last")

        hooks = [
            ModelPipelineHook(
                hook_id="sync_first", phase="execute", callable_ref="test.sync_first"
            ),
            ModelPipelineHook(
                hook_id="async_middle",
                phase="execute",
                callable_ref="test.async_middle",
            ),
            ModelPipelineHook(
                hook_id="sync_last", phase="execute", callable_ref="test.sync_last"
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={
                "test.sync_first": sync_first,
                "test.async_middle": async_middle,
                "test.sync_last": sync_last,
            },
        )
        await runner.run()

        assert execution_order == ["sync_first", "async_middle", "sync_last"]


@pytest.mark.unit
class TestRunnerPipelineEmptyPipeline:
    """Test behavior with no hooks."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_hooks_succeeds(self) -> None:
        """Pipeline with no hooks completes successfully."""
        plan = ModelExecutionPlan.empty()
        runner = RunnerPipeline(plan=plan, callable_registry={})
        result = await runner.run()
        assert result.success

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_phases_succeed(self) -> None:
        """Pipeline with empty phases completes successfully."""
        plan = make_plan_with_hooks()
        runner = RunnerPipeline(plan=plan, callable_registry={})
        result = await runner.run()
        assert result.success


@pytest.mark.unit
class TestRunnerPipelineModelPipelineContext:
    """Test ModelPipelineContext behavior."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_shared_across_hooks(self) -> None:
        """Context is shared and mutable across hooks."""

        def first(ctx: ModelPipelineContext) -> None:
            ctx.data["from_first"] = "value1"

        def second(ctx: ModelPipelineContext) -> None:
            ctx.data["from_second"] = ctx.data.get("from_first", "") + "_modified"

        hooks = [
            ModelPipelineHook(
                hook_id="first", phase="execute", callable_ref="test.first"
            ),
            ModelPipelineHook(
                hook_id="second", phase="execute", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )
        result = await runner.run()

        assert result.context is not None
        assert result.context.data["from_first"] == "value1"
        assert result.context.data["from_second"] == "value1_modified"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_preserved_across_phases(self) -> None:
        """Context data persists across phases."""

        def preflight_hook(ctx: ModelPipelineContext) -> None:
            ctx.data["phase"] = ["preflight"]

        def execute_hook(ctx: ModelPipelineContext) -> None:
            ctx.data["phase"].append("execute")

        def finalize_hook(ctx: ModelPipelineContext) -> None:
            ctx.data["phase"].append("finalize")

        hooks_by_phase = [
            (
                "preflight",
                [
                    ModelPipelineHook(
                        hook_id="preflight",
                        phase="preflight",
                        callable_ref="test.preflight",
                    )
                ],
            ),
            (
                "execute",
                [
                    ModelPipelineHook(
                        hook_id="execute", phase="execute", callable_ref="test.execute"
                    )
                ],
            ),
            (
                "finalize",
                [
                    ModelPipelineHook(
                        hook_id="finalize",
                        phase="finalize",
                        callable_ref="test.finalize",
                    )
                ],
            ),
        ]
        plan = make_plan_with_hooks(*hooks_by_phase)  # type: ignore[arg-type]

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={
                "test.preflight": preflight_hook,
                "test.execute": execute_hook,
                "test.finalize": finalize_hook,
            },
        )
        result = await runner.run()

        assert result.context is not None
        assert result.context.data["phase"] == ["preflight", "execute", "finalize"]


@pytest.mark.unit
class TestRunnerPipelineModelPipelineResult:
    """Test ModelPipelineResult behavior."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_success_when_no_errors(self) -> None:
        """Result is successful when no errors occurred."""

        def ok_hook(ctx: ModelPipelineContext) -> None:
            pass

        hooks = [
            ModelPipelineHook(hook_id="ok", phase="execute", callable_ref="test.ok")
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(plan=plan, callable_registry={"test.ok": ok_hook})
        result = await runner.run()

        assert result.success is True
        assert len(result.errors) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_contains_errors_from_continue_phases(self) -> None:
        """Result contains captured errors from continue phases."""

        def failing_hook(ctx: ModelPipelineContext) -> None:
            raise RuntimeError("Expected error")

        hooks = [
            ModelPipelineHook(
                hook_id="failing", phase="after", callable_ref="test.failing"
            )
        ]
        plan = make_plan_with_hooks(("after", hooks))

        runner = RunnerPipeline(
            plan=plan, callable_registry={"test.failing": failing_hook}
        )
        result = await runner.run()

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].hook_id == "failing"
        assert result.errors[0].phase == "after"
        assert "RuntimeError" in result.errors[0].error_type


@pytest.mark.unit
class TestRunnerPipelineCallableResolution:
    """Test callable registry resolution."""

    @pytest.mark.unit
    def test_missing_callable_raises_error_at_init(self) -> None:
        """Missing callable in registry raises error at __init__ time (fail-fast)."""
        hooks = [
            ModelPipelineHook(
                hook_id="missing",
                phase="execute",
                callable_ref="test.nonexistent",
            )
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        # Error should be raised at initialization, not at run()
        with pytest.raises(CallableNotFoundError, match=r"test\.nonexistent"):
            RunnerPipeline(plan=plan, callable_registry={})

    @pytest.mark.unit
    def test_multiple_missing_callables_lists_all_in_error(self) -> None:
        """Multiple missing callables are all listed in the error message."""
        hooks = [
            ModelPipelineHook(
                hook_id="first",
                phase="execute",
                callable_ref="test.missing_one",
            ),
            ModelPipelineHook(
                hook_id="second",
                phase="execute",
                callable_ref="test.missing_two",
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        with pytest.raises(CallableNotFoundError) as exc_info:
            RunnerPipeline(plan=plan, callable_registry={})

        error_message = str(exc_info.value)
        assert "test.missing_one" in error_message
        assert "test.missing_two" in error_message
        assert "Multiple missing callable_refs" in error_message

    @pytest.mark.unit
    def test_missing_callable_across_phases_detected_at_init(self) -> None:
        """Missing callables across multiple phases are detected at init."""
        hooks_by_phase = [
            (
                "preflight",
                [
                    ModelPipelineHook(
                        hook_id="preflight_hook",
                        phase="preflight",
                        callable_ref="test.preflight_missing",
                    )
                ],
            ),
            (
                "execute",
                [
                    ModelPipelineHook(
                        hook_id="execute_hook",
                        phase="execute",
                        callable_ref="test.execute_missing",
                    )
                ],
            ),
        ]
        plan = make_plan_with_hooks(*hooks_by_phase)  # type: ignore[arg-type]

        with pytest.raises(CallableNotFoundError) as exc_info:
            RunnerPipeline(plan=plan, callable_registry={})

        error_message = str(exc_info.value)
        assert "test.preflight_missing" in error_message
        assert "test.execute_missing" in error_message

    @pytest.mark.unit
    def test_partial_registry_detects_only_missing(self) -> None:
        """Only missing callables are reported, not ones that exist."""

        def existing_hook(ctx: ModelPipelineContext) -> None:
            pass

        hooks = [
            ModelPipelineHook(
                hook_id="exists",
                phase="execute",
                callable_ref="test.exists",
            ),
            ModelPipelineHook(
                hook_id="missing",
                phase="execute",
                callable_ref="test.missing",
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        # Partial registry - one callable exists, one doesn't
        with pytest.raises(CallableNotFoundError) as exc_info:
            RunnerPipeline(plan=plan, callable_registry={"test.exists": existing_hook})

        error_message = str(exc_info.value)
        assert "test.missing" in error_message
        assert "test.exists" not in error_message

    @pytest.mark.unit
    def test_empty_plan_no_validation_error(self) -> None:
        """Empty plan with empty registry succeeds initialization."""
        plan = ModelExecutionPlan.empty()
        # Should not raise
        runner = RunnerPipeline(plan=plan, callable_registry={})
        assert runner is not None

    @pytest.mark.unit
    def test_callable_registry_is_immutable(self) -> None:
        """
        Callable registry is immutable after initialization.

        The registry uses MappingProxyType to prevent accidental modification.
        This is better than defense-in-depth runtime checks because mutation
        is impossible, not just detected.
        """

        def hook_fn(ctx: ModelPipelineContext) -> None:
            pass

        hooks = [
            ModelPipelineHook(
                hook_id="test",
                phase="execute",
                callable_ref="test.hook",
            )
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(plan=plan, callable_registry={"test.hook": hook_fn})

        # MappingProxyType prevents mutation
        with pytest.raises(TypeError):
            runner._callable_registry["new_key"] = hook_fn  # type: ignore[index]

        # Verify original callable is still accessible
        assert runner._callable_registry["test.hook"] is hook_fn


@pytest.mark.unit
class TestRunnerPipelineComplexPipeline:
    """Test complex pipeline scenarios."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_pipeline_with_all_phases(self) -> None:
        """Full pipeline executes all phases correctly."""
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: ModelPipelineContext) -> None:
                execution_order.append(name)

            return hook

        all_phases: list[PipelinePhase] = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        hooks_by_phase = []
        callables: dict[str, HookCallable] = {}

        for phase in all_phases:
            hook = ModelPipelineHook(
                hook_id=f"{phase}-hook",
                phase=phase,
                callable_ref=f"test.{phase}",
            )
            hooks_by_phase.append((phase, [hook]))
            callables[f"test.{phase}"] = make_hook(phase)

        plan = make_plan_with_hooks(*hooks_by_phase)  # type: ignore[arg-type]
        runner = RunnerPipeline(plan=plan, callable_registry=callables)
        result = await runner.run()

        assert result.success
        assert execution_order == list(all_phases)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fail_fast_phase_stops_pipeline_but_finalize_runs(self) -> None:
        """Fail-fast phase stops pipeline, but finalize still runs."""
        execution_order: list[str] = []

        def preflight_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("preflight")

        def failing_before(ctx: ModelPipelineContext) -> None:
            execution_order.append("before")
            raise ValueError("Before failed")

        def execute_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("execute")  # Should never run

        def finalize_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("finalize")  # Must still run

        hooks_by_phase = [
            (
                "preflight",
                [
                    ModelPipelineHook(
                        hook_id="preflight",
                        phase="preflight",
                        callable_ref="test.preflight",
                    )
                ],
            ),
            (
                "before",
                [
                    ModelPipelineHook(
                        hook_id="before", phase="before", callable_ref="test.before"
                    )
                ],
            ),
            (
                "execute",
                [
                    ModelPipelineHook(
                        hook_id="execute", phase="execute", callable_ref="test.execute"
                    )
                ],
            ),
            (
                "finalize",
                [
                    ModelPipelineHook(
                        hook_id="finalize",
                        phase="finalize",
                        callable_ref="test.finalize",
                    )
                ],
            ),
        ]
        plan = make_plan_with_hooks(*hooks_by_phase)  # type: ignore[arg-type]

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={
                "test.preflight": preflight_hook,
                "test.before": failing_before,
                "test.execute": execute_hook,
                "test.finalize": finalize_hook,
            },
        )

        with pytest.raises(ValueError, match="Before failed"):
            await runner.run()

        # Preflight ran, before ran and failed, execute skipped, finalize ran
        assert execution_order == ["preflight", "before", "finalize"]


@pytest.mark.unit
class TestRunnerPipelineTimeoutEnforcement:
    """Test timeout enforcement for hooks."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_hook_timeout_raises_hook_timeout_error(self) -> None:
        """Async hook that exceeds timeout raises HookTimeoutError."""
        import asyncio

        from omnibase_core.pipeline.exceptions import HookTimeoutError

        async def slow_hook(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(1.0)  # Sleep longer than timeout

        hook = ModelPipelineHook(
            hook_id="slow",
            phase="execute",
            callable_ref="test.slow",
            timeout_seconds=0.1,  # 100ms timeout
        )
        plan = make_plan_with_hooks(("execute", [hook]))

        runner = RunnerPipeline(plan=plan, callable_registry={"test.slow": slow_hook})

        with pytest.raises(HookTimeoutError) as exc_info:
            await runner.run()

        # Verify error message contains expected info
        assert "slow" in str(exc_info.value)
        assert "0.1" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_hook_timeout_raises_hook_timeout_error(self) -> None:
        """Sync hook that exceeds timeout raises HookTimeoutError."""
        import time

        from omnibase_core.pipeline.exceptions import HookTimeoutError

        def slow_sync_hook(ctx: ModelPipelineContext) -> None:
            time.sleep(1.0)  # Sleep longer than timeout

        hook = ModelPipelineHook(
            hook_id="slow_sync",
            phase="execute",
            callable_ref="test.slow_sync",
            timeout_seconds=0.1,  # 100ms timeout
        )
        plan = make_plan_with_hooks(("execute", [hook]))

        runner = RunnerPipeline(
            plan=plan, callable_registry={"test.slow_sync": slow_sync_hook}
        )

        with pytest.raises(HookTimeoutError) as exc_info:
            await runner.run()

        # Verify error message contains expected info
        assert "slow_sync" in str(exc_info.value)
        assert "0.1" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_hook_completes_within_timeout(self) -> None:
        """Async hook that completes within timeout succeeds."""
        import asyncio

        executed: list[bool] = []

        async def fast_hook(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(0.01)  # Sleep less than timeout
            executed.append(True)

        hook = ModelPipelineHook(
            hook_id="fast",
            phase="execute",
            callable_ref="test.fast",
            timeout_seconds=1.0,  # 1 second timeout
        )
        plan = make_plan_with_hooks(("execute", [hook]))

        runner = RunnerPipeline(plan=plan, callable_registry={"test.fast": fast_hook})
        result = await runner.run()

        assert result.success is True
        assert executed == [True]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_hook_completes_within_timeout(self) -> None:
        """Sync hook that completes within timeout succeeds."""
        import time

        executed: list[bool] = []

        def fast_sync_hook(ctx: ModelPipelineContext) -> None:
            time.sleep(0.01)  # Sleep less than timeout
            executed.append(True)

        hook = ModelPipelineHook(
            hook_id="fast_sync",
            phase="execute",
            callable_ref="test.fast_sync",
            timeout_seconds=1.0,  # 1 second timeout
        )
        plan = make_plan_with_hooks(("execute", [hook]))

        runner = RunnerPipeline(
            plan=plan, callable_registry={"test.fast_sync": fast_sync_hook}
        )
        result = await runner.run()

        assert result.success is True
        assert executed == [True]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hook_without_timeout_no_enforcement(self) -> None:
        """Hook without timeout_seconds runs without timeout enforcement."""
        import asyncio

        executed: list[bool] = []

        async def hook_no_timeout(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(0.05)  # Would timeout if enforced at 0.01s
            executed.append(True)

        hook = ModelPipelineHook(
            hook_id="no_timeout",
            phase="execute",
            callable_ref="test.no_timeout",
            # No timeout_seconds specified - defaults to None
        )
        plan = make_plan_with_hooks(("execute", [hook]))

        runner = RunnerPipeline(
            plan=plan, callable_registry={"test.no_timeout": hook_no_timeout}
        )
        result = await runner.run()

        assert result.success is True
        assert executed == [True]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_in_continue_phase_captured_as_error(self) -> None:
        """Timeout in continue phase (after) is captured, not raised."""
        import asyncio

        async def slow_after_hook(ctx: ModelPipelineContext) -> None:
            await asyncio.sleep(1.0)

        hook = ModelPipelineHook(
            hook_id="slow_after",
            phase="after",
            callable_ref="test.slow_after",
            timeout_seconds=0.1,
        )
        plan = make_plan_with_hooks(("after", [hook]))

        runner = RunnerPipeline(
            plan=plan, callable_registry={"test.slow_after": slow_after_hook}
        )
        result = await runner.run()

        # Continue phase captures errors
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].hook_id == "slow_after"
        assert "HookTimeoutError" in result.errors[0].error_type

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_in_fail_fast_phase_raises_immediately(self) -> None:
        """Timeout in fail-fast phase (execute) raises immediately."""
        import asyncio

        from omnibase_core.pipeline.exceptions import HookTimeoutError

        execution_order: list[str] = []

        async def slow_execute_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("slow_start")
            await asyncio.sleep(1.0)
            execution_order.append("slow_end")  # Should never reach

        def second_hook(ctx: ModelPipelineContext) -> None:
            execution_order.append("second")  # Should never run

        hooks = [
            ModelPipelineHook(
                hook_id="slow",
                phase="execute",
                callable_ref="test.slow",
                timeout_seconds=0.1,
            ),
            ModelPipelineHook(
                hook_id="second",
                phase="execute",
                callable_ref="test.second",
            ),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = RunnerPipeline(
            plan=plan,
            callable_registry={
                "test.slow": slow_execute_hook,
                "test.second": second_hook,
            },
        )

        with pytest.raises(HookTimeoutError):
            await runner.run()

        # Only slow_start executed before timeout
        assert execution_order == ["slow_start"]


@pytest.mark.unit
class TestRunnerPipelineExceptionModels:
    """Test exception classes follow project patterns."""

    @pytest.mark.unit
    def test_callable_not_found_error_has_correct_error_code(self) -> None:
        """CallableNotFoundError uses NOT_FOUND error code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.pipeline.exceptions import CallableNotFoundError

        error = CallableNotFoundError("missing.callable")

        assert error.error_code == EnumCoreErrorCode.NOT_FOUND
        assert "missing.callable" in str(error)
        # Context is stored in additional_context -> context for custom keys
        additional = error.context.get("additional_context", {})
        context_dict = additional.get("context", {})
        assert context_dict.get("callable_ref") == "missing.callable"

    @pytest.mark.unit
    def test_hook_timeout_error_has_correct_error_code(self) -> None:
        """HookTimeoutError uses TIMEOUT error code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.pipeline.exceptions import HookTimeoutError

        error = HookTimeoutError("my_hook", 5.0)

        assert error.error_code == EnumCoreErrorCode.TIMEOUT
        assert "my_hook" in str(error)
        assert "5.0" in str(error)
        # Context is stored in additional_context -> context for custom keys
        additional = error.context.get("additional_context", {})
        context_dict = additional.get("context", {})
        assert context_dict.get("hook_id") == "my_hook"
        assert context_dict.get("timeout_seconds") == 5.0

    @pytest.mark.unit
    def test_exceptions_inherit_from_pipeline_error(self) -> None:
        """Pipeline exceptions inherit from PipelineError."""
        from omnibase_core.pipeline.exceptions import (
            CallableNotFoundError,
            HookTimeoutError,
            PipelineError,
        )

        callable_err = CallableNotFoundError("test")
        timeout_err = HookTimeoutError("hook", 1.0)

        assert isinstance(callable_err, PipelineError)
        assert isinstance(timeout_err, PipelineError)

    @pytest.mark.unit
    def test_exceptions_inherit_from_model_onex_error(self) -> None:
        """Pipeline exceptions ultimately inherit from ModelOnexError."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.pipeline.exceptions import (
            CallableNotFoundError,
            HookTimeoutError,
        )

        callable_err = CallableNotFoundError("test")
        timeout_err = HookTimeoutError("hook", 1.0)

        assert isinstance(callable_err, ModelOnexError)
        assert isinstance(timeout_err, ModelOnexError)
