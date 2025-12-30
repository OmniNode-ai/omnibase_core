# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for PipelineRunner."""
from collections.abc import Callable, Coroutine

import pytest

from omnibase_core.pipeline.models import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineHook,
    PipelinePhase,
)
from omnibase_core.pipeline.pipeline_runner import (
    HookCallable,
    PipelineContext,
    PipelineResult,
    PipelineRunner,
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
class TestPhaseExecutionOrder:
    """Test hooks execute in canonical phase order."""

    @pytest.mark.asyncio
    async def test_phases_execute_in_order(self) -> None:
        """Phases execute in canonical order."""
        execution_order: list[str] = []

        def make_hook_callable(phase_name: str) -> HookCallable:
            def hook(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(plan=plan, callable_registry=callables)
        await runner.run()

        assert execution_order == [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]

    @pytest.mark.asyncio
    async def test_hooks_within_phase_execute_in_plan_order(self) -> None:
        """Hooks within a phase execute in the order from the plan."""
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(plan=plan, callable_registry=callables)
        await runner.run()

        assert execution_order == ["first", "second", "third"]


@pytest.mark.unit
class TestFinalizeAlwaysRuns:
    """Test finalize phase ALWAYS runs."""

    @pytest.mark.asyncio
    async def test_finalize_runs_on_success(self) -> None:
        """Finalize runs after successful execution."""
        finalize_ran: list[bool] = []

        def finalize_hook(ctx: PipelineContext) -> None:
            finalize_ran.append(True)

        hooks = [
            ModelPipelineHook(
                hook_id="finalize",
                phase="finalize",
                callable_ref="test.finalize",
            )
        ]
        plan = make_plan_with_hooks(("finalize", hooks))

        runner = PipelineRunner(
            plan=plan, callable_registry={"test.finalize": finalize_hook}
        )
        await runner.run()

        assert finalize_ran == [True]

    @pytest.mark.asyncio
    async def test_finalize_runs_on_exception(self) -> None:
        """Finalize runs even when earlier phase raises exception."""
        finalize_ran: list[bool] = []

        def failing_hook(ctx: PipelineContext) -> None:
            raise ValueError("Intentional failure")

        def finalize_hook_fn(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
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
class TestErrorHandlingPerPhase:
    """Test error handling behavior per phase."""

    @pytest.mark.asyncio
    async def test_preflight_fails_fast(self) -> None:
        """Preflight phase aborts on first error."""
        execution_order: list[str] = []

        def first(ctx: PipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Preflight failed")

        def second(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        with pytest.raises(ValueError):
            await runner.run()

        assert execution_order == ["first"]  # Second never ran

    @pytest.mark.asyncio
    async def test_before_fails_fast(self) -> None:
        """Before phase aborts on first error."""
        execution_order: list[str] = []

        def first(ctx: PipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Before failed")

        def second(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        with pytest.raises(ValueError):
            await runner.run()

        assert execution_order == ["first"]  # Second never ran

    @pytest.mark.asyncio
    async def test_execute_fails_fast(self) -> None:
        """Execute phase aborts on first error."""
        execution_order: list[str] = []

        def first(ctx: PipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Execute failed")

        def second(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        with pytest.raises(ValueError):
            await runner.run()

        assert execution_order == ["first"]  # Second never ran

    @pytest.mark.asyncio
    async def test_after_phase_continues_on_error(self) -> None:
        """After phase continues despite errors."""
        execution_order: list[str] = []

        def first(ctx: PipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("After hook failed")

        def second(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        # Should not raise, continues on error
        result = await runner.run()

        assert execution_order == ["first", "second"]  # Both ran
        assert len(result.errors) > 0  # Error was captured

    @pytest.mark.asyncio
    async def test_emit_phase_continues_on_error(self) -> None:
        """Emit phase continues despite errors."""
        execution_order: list[str] = []

        def first(ctx: PipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Emit hook failed")

        def second(ctx: PipelineContext) -> None:
            execution_order.append("second")

        hooks = [
            ModelPipelineHook(hook_id="first", phase="emit", callable_ref="test.first"),
            ModelPipelineHook(
                hook_id="second", phase="emit", callable_ref="test.second"
            ),
        ]
        plan = make_plan_with_hooks(("emit", hooks))

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        # Should not raise, continues on error
        result = await runner.run()

        assert execution_order == ["first", "second"]  # Both ran
        assert len(result.errors) > 0  # Error was captured

    @pytest.mark.asyncio
    async def test_finalize_phase_continues_on_error(self) -> None:
        """Finalize phase continues despite errors."""
        execution_order: list[str] = []

        def first(ctx: PipelineContext) -> None:
            execution_order.append("first")
            raise ValueError("Finalize hook failed")

        def second(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )

        # Should not raise, finalize always continues
        result = await runner.run()

        assert execution_order == ["first", "second"]  # Both ran
        assert len(result.errors) > 0  # Error was captured


@pytest.mark.unit
class TestAsyncHookSupport:
    """Test async hook support."""

    @pytest.mark.asyncio
    async def test_async_hook_awaited(self) -> None:
        """Async hooks are properly awaited."""
        execution_order: list[str] = []

        async def async_hook(ctx: PipelineContext) -> None:
            execution_order.append("async")

        def sync_hook(ctx: PipelineContext) -> None:
            execution_order.append("sync")

        hooks = [
            ModelPipelineHook(
                hook_id="async", phase="execute", callable_ref="test.async"
            ),
            ModelPipelineHook(hook_id="sync", phase="execute", callable_ref="test.sync"),
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.async": async_hook, "test.sync": sync_hook},
        )
        await runner.run()

        assert execution_order == ["async", "sync"]

    @pytest.mark.asyncio
    async def test_mixed_sync_async_hooks(self) -> None:
        """Mixed sync and async hooks execute correctly."""
        execution_order: list[str] = []

        def sync_first(ctx: PipelineContext) -> None:
            execution_order.append("sync_first")

        async def async_middle(ctx: PipelineContext) -> None:
            execution_order.append("async_middle")

        def sync_last(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
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
class TestEmptyPipeline:
    """Test behavior with no hooks."""

    @pytest.mark.asyncio
    async def test_no_hooks_succeeds(self) -> None:
        """Pipeline with no hooks completes successfully."""
        plan = ModelExecutionPlan.empty()
        runner = PipelineRunner(plan=plan, callable_registry={})
        result = await runner.run()
        assert result.success

    @pytest.mark.asyncio
    async def test_empty_phases_succeed(self) -> None:
        """Pipeline with empty phases completes successfully."""
        plan = make_plan_with_hooks()
        runner = PipelineRunner(plan=plan, callable_registry={})
        result = await runner.run()
        assert result.success


@pytest.mark.unit
class TestPipelineContext:
    """Test PipelineContext behavior."""

    @pytest.mark.asyncio
    async def test_context_shared_across_hooks(self) -> None:
        """Context is shared and mutable across hooks."""

        def first(ctx: PipelineContext) -> None:
            ctx.data["from_first"] = "value1"

        def second(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
            plan=plan,
            callable_registry={"test.first": first, "test.second": second},
        )
        result = await runner.run()

        assert result.context is not None
        assert result.context.data["from_first"] == "value1"
        assert result.context.data["from_second"] == "value1_modified"

    @pytest.mark.asyncio
    async def test_context_preserved_across_phases(self) -> None:
        """Context data persists across phases."""

        def preflight_hook(ctx: PipelineContext) -> None:
            ctx.data["phase"] = ["preflight"]

        def execute_hook(ctx: PipelineContext) -> None:
            ctx.data["phase"].append("execute")

        def finalize_hook(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
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
class TestPipelineResult:
    """Test PipelineResult behavior."""

    @pytest.mark.asyncio
    async def test_result_success_when_no_errors(self) -> None:
        """Result is successful when no errors occurred."""

        def ok_hook(ctx: PipelineContext) -> None:
            pass

        hooks = [
            ModelPipelineHook(hook_id="ok", phase="execute", callable_ref="test.ok")
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = PipelineRunner(plan=plan, callable_registry={"test.ok": ok_hook})
        result = await runner.run()

        assert result.success is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_result_contains_errors_from_continue_phases(self) -> None:
        """Result contains captured errors from continue phases."""

        def failing_hook(ctx: PipelineContext) -> None:
            raise RuntimeError("Expected error")

        hooks = [
            ModelPipelineHook(
                hook_id="failing", phase="after", callable_ref="test.failing"
            )
        ]
        plan = make_plan_with_hooks(("after", hooks))

        runner = PipelineRunner(
            plan=plan, callable_registry={"test.failing": failing_hook}
        )
        result = await runner.run()

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].hook_id == "failing"
        assert result.errors[0].phase == "after"
        assert "RuntimeError" in result.errors[0].error_type


@pytest.mark.unit
class TestCallableResolution:
    """Test callable registry resolution."""

    @pytest.mark.asyncio
    async def test_missing_callable_raises_error(self) -> None:
        """Missing callable in registry raises an error."""
        hooks = [
            ModelPipelineHook(
                hook_id="missing",
                phase="execute",
                callable_ref="test.nonexistent",
            )
        ]
        plan = make_plan_with_hooks(("execute", hooks))

        runner = PipelineRunner(plan=plan, callable_registry={})

        with pytest.raises(KeyError, match="test.nonexistent"):
            await runner.run()


@pytest.mark.unit
class TestComplexPipeline:
    """Test complex pipeline scenarios."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_all_phases(self) -> None:
        """Full pipeline executes all phases correctly."""
        execution_order: list[str] = []

        def make_hook(name: str) -> HookCallable:
            def hook(ctx: PipelineContext) -> None:
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
        runner = PipelineRunner(plan=plan, callable_registry=callables)
        result = await runner.run()

        assert result.success
        assert execution_order == list(all_phases)

    @pytest.mark.asyncio
    async def test_fail_fast_phase_stops_pipeline_but_finalize_runs(self) -> None:
        """Fail-fast phase stops pipeline, but finalize still runs."""
        execution_order: list[str] = []

        def preflight_hook(ctx: PipelineContext) -> None:
            execution_order.append("preflight")

        def failing_before(ctx: PipelineContext) -> None:
            execution_order.append("before")
            raise ValueError("Before failed")

        def execute_hook(ctx: PipelineContext) -> None:
            execution_order.append("execute")  # Should never run

        def finalize_hook(ctx: PipelineContext) -> None:
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

        runner = PipelineRunner(
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
