"""Pipeline runner for executing hooks in canonical phase order."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Coroutine
from types import MappingProxyType

from omnibase_core.models.pipeline import (
    ModelHookError,
    ModelPipelineContext,
    ModelPipelineExecutionPlan,
    ModelPipelineHook,
    ModelPipelineResult,
    PipelinePhase,
)
from omnibase_core.pipeline.exceptions import CallableNotFoundError, HookTimeoutError

# Type alias for hook callables - they take ModelPipelineContext and return None
# (sync or async)
HookCallable = Callable[
    ["ModelPipelineContext"], None | Coroutine[object, object, None]
]


# Canonical phase execution order
CANONICAL_PHASE_ORDER: list[PipelinePhase] = [
    "preflight",
    "before",
    "execute",
    "after",
    "emit",
    "finalize",
]


class RunnerPipeline:
    """
    Executes hooks in the canonical phase order using an execution plan.

    The runner handles:
    - Phase execution order: preflight -> before -> execute -> after -> emit -> finalize
    - Sync and async hook execution
    - Error handling per phase:
        - preflight, before, execute: fail-fast (abort on first error)
        - after, emit, finalize: continue (collect errors, run all hooks)
    - Finalize ALWAYS runs, even if earlier phases raise exceptions

    Thread Safety
    -------------
    **CRITICAL**: This class is NOT thread-safe during execution (intentional design).

    **Thread Safety Matrix:**

    ===============================  ==============  =====================================
    Component                        Thread-Safe?    Notes
    ===============================  ==============  =====================================
    RunnerPipeline instance          No              Mutable state during run()
    ModelPipelineExecutionPlan        Yes             Frozen Pydantic model (frozen=True)
    ModelPhaseExecutionPlan          Yes             Frozen Pydantic model (frozen=True)
    ModelPipelineHook                Yes             Frozen Pydantic model (frozen=True)
    ModelPipelineContext             No              Mutable dict for hook communication
    ModelPipelineResult              Yes             Frozen Pydantic model (frozen=True)
    ModelHookError                   Yes             Frozen Pydantic model (frozen=True)
    callable_registry dict           Conditional     Safe if not modified after init
    ===============================  ==============  =====================================

    **Usage Patterns:**

    Incorrect - Sharing runner across threads::

        # UNSAFE - concurrent execution will have race conditions
        runner = RunnerPipeline(plan, registry)

        async def worker_1():
            await runner.run()  # Race on context state!

        async def worker_2():
            await runner.run()  # Race on context state!

    Correct - Separate instance per execution::

        # SAFE - each execution gets its own runner
        def create_runner():
            return RunnerPipeline(plan, registry)  # plan is safely shared

        async def worker_1():
            runner = create_runner()
            await runner.run()  # Isolated execution

        async def worker_2():
            runner = create_runner()
            await runner.run()  # Isolated execution

    **Design Rationale:**

    The runner is intentionally NOT thread-safe for these reasons:

    1. **Performance**: Synchronization adds overhead to every hook execution
    2. **Simplicity**: Per-execution instances are simpler to reason about
    3. **AsyncIO Compatibility**: Most pipeline workloads use asyncio single-threaded
    4. **Explicit Control**: Callers must consciously choose concurrency model

    **Safe Sharing:**

    - ``ModelPipelineExecutionPlan`` is frozen and can be safely shared across threads
    - ``callable_registry`` dict can be shared IF not modified after runner creation
    - Use ``plan.model_copy()`` if you need isolated plan modifications

    See Also
    --------
    - docs/guides/THREADING.md for comprehensive thread safety guide
    - CLAUDE.md section "Thread Safety" for quick reference
    """

    def __init__(
        self,
        plan: ModelPipelineExecutionPlan,
        callable_registry: dict[str, HookCallable],
    ) -> None:
        """
        Initialize the pipeline runner.

        Args:
            plan: The execution plan containing hooks organized by phase
            callable_registry: Registry mapping callable_ref strings to actual callables.
                An immutable view is created to prevent accidental modification.

        Raises:
            CallableNotFoundError: If any hook's callable_ref is not in the registry.
                This fail-fast validation prevents runtime surprises.
        """
        self._plan = plan
        self._callable_registry = MappingProxyType(callable_registry)

        # Fail-fast: validate all callable_refs at initialization time
        self._validate_callable_refs()

    def _validate_callable_refs(self) -> None:
        """
        Validate that all callable_refs in the plan exist in the registry.

        Raises:
            CallableNotFoundError: If any callable_ref is missing from the registry.
                The error message lists all missing refs for easier debugging.
        """
        missing_refs: list[str] = []

        for phase_plan in self._plan.phases.values():
            for hook in phase_plan.hooks:
                if hook.callable_ref not in self._callable_registry:
                    missing_refs.append(hook.callable_ref)

        if missing_refs:
            # Sort for deterministic error messages in tests
            missing_refs.sort()
            if len(missing_refs) == 1:
                raise CallableNotFoundError(missing_refs[0])
            # For multiple missing refs, include all in the message
            raise CallableNotFoundError(
                f"Multiple missing callable_refs: {', '.join(missing_refs)}"
            )

    async def run(self) -> ModelPipelineResult:
        """
        Execute the pipeline.

        Returns:
            ModelPipelineResult containing success status, errors, and context

        Raises:
            Exception: Re-raises exceptions from fail-fast phases
            CallableNotFoundError: If a hook's callable_ref is not in the registry
        """
        context = ModelPipelineContext()
        errors: list[ModelHookError] = []
        exception_to_raise: Exception | None = None

        try:
            # Execute all phases except finalize
            for phase in CANONICAL_PHASE_ORDER[:-1]:  # All except finalize
                try:
                    phase_errors = await self._execute_phase(phase, context)
                    errors.extend(phase_errors)
                # boundary-ok: captures phase exceptions for controlled shutdown; finalize phase still runs
                except Exception as e:
                    # catch-all-ok: fail-fast phase raised exception, captured for re-raise after finalize
                    exception_to_raise = e
                    break  # Stop executing phases, but finalize will still run
        finally:
            # Finalize phase is extracted for clarity and always runs
            finalize_errors = await self._execute_finalize_phase(context)
            errors.extend(finalize_errors)

        # Re-raise exception from fail-fast phase if any
        if exception_to_raise is not None:
            raise exception_to_raise

        return ModelPipelineResult(
            success=len(errors) == 0,
            errors=tuple(errors),
            context=context,
        )

    async def _execute_finalize_phase(
        self,
        context: ModelPipelineContext,
    ) -> list[ModelHookError]:
        """
        Execute the finalize phase with guaranteed error capture.

        The finalize phase ALWAYS runs regardless of earlier phase failures.
        It uses continue-on-error semantics (fail_fast=False) so all finalize
        hooks execute even if some fail.

        This method wraps finalize execution to ensure:
        1. Hook-level errors are captured with proper hook_name context
        2. Framework-level errors (outside hook execution) are captured gracefully
        3. No exception escapes - all errors become ModelHookError entries

        Args:
            context: The shared pipeline context

        Returns:
            List of errors captured during finalize (never raises)
        """
        errors: list[ModelHookError] = []
        current_hook_name: str | None = None

        try:
            # Get hooks to track which hook we're executing for error context
            hooks = self._plan.get_phase_hooks("finalize")

            for hook in hooks:
                current_hook_name = hook.hook_name
                try:
                    await self._execute_hook(hook, context)
                    # Only clear hook_name after successful execution
                    current_hook_name = None
                # cleanup-resilience-ok: finalize hooks must all execute; errors captured, not raised
                except Exception as e:
                    # catch-all-ok: finalize hooks must complete; errors captured for reporting
                    errors.append(
                        ModelHookError(
                            phase="finalize",
                            hook_name=hook.hook_name,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )
                    )
                    # Clear after capturing - hook processing complete
                    current_hook_name = None

        # boundary-ok: framework-level errors during finalize become ModelHookError, never raised
        except Exception as framework_exc:
            # catch-all-ok: framework-level error captured for error list, no exception escapes finalize
            # Include last known hook_name if available for debugging context
            hook_name_context = (
                f"[framework:after:{current_hook_name}]"
                if current_hook_name
                else "[framework]"
            )
            errors.append(
                ModelHookError(
                    phase="finalize",
                    hook_name=hook_name_context,
                    error_type=type(framework_exc).__name__,
                    error_message=f"Framework error during finalize phase: {framework_exc}",
                )
            )

        return errors

    async def _execute_phase(
        self,
        phase: PipelinePhase,
        context: ModelPipelineContext,
    ) -> list[ModelHookError]:
        """
        Execute all hooks in a phase.

        Phase Semantics (fail_fast behavior):
            - **preflight, before, execute**: fail_fast=True
              Abort immediately on first error. These phases must complete
              successfully for the pipeline to be in a valid state.
            - **after, emit, finalize**: fail_fast=False
              Continue executing remaining hooks even if one fails. Errors are
              collected and returned. These phases handle cleanup/notification
              where partial execution is acceptable.

        Note:
            The fail_fast behavior is determined by the execution plan via
            ``self._plan.is_phase_fail_fast(phase)``. The semantic defaults above
            match CANONICAL_PHASE_ORDER but can be overridden in custom plans.

        Args:
            phase: The phase to execute
            context: The shared pipeline context

        Returns:
            List of errors captured (for continue phases, i.e., fail_fast=False)

        Raises:
            Exception: For fail-fast phases, re-raises the first exception
        """
        hooks = self._plan.get_phase_hooks(phase)
        # Fail-fast semantics: preflight/before/execute abort on error,
        # after/emit/finalize continue and collect errors
        fail_fast = self._plan.is_phase_fail_fast(phase)
        errors: list[ModelHookError] = []

        for hook in hooks:
            try:
                await self._execute_hook(hook, context)
            # boundary-ok: hook exceptions captured; re-raised for fail-fast phases, collected otherwise
            except Exception as e:
                # catch-all-ok: hook execution errors captured for phase semantics
                if fail_fast:
                    # Re-raise immediately for fail-fast phases
                    raise
                # Capture error and continue for continue phases
                errors.append(
                    ModelHookError(
                        phase=phase,
                        hook_name=hook.hook_name,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                )

        return errors

    async def _execute_hook(
        self,
        hook: ModelPipelineHook,
        context: ModelPipelineContext,
    ) -> None:
        """
        Execute a single hook.

        If the hook has a timeout_seconds configured, the callable will be
        wrapped with asyncio.wait_for() to enforce the timeout. For sync
        callables, asyncio.to_thread() is used to allow timeout enforcement.

        Args:
            hook: The hook to execute
            context: The shared pipeline context

        Raises:
            CallableNotFoundError: If the hook's callable_ref is not in the registry
            HookTimeoutError: If the hook exceeds its configured timeout
            Exception: Any exception raised by the hook callable
        """
        callable_ref = hook.callable_ref

        if callable_ref not in self._callable_registry:
            raise CallableNotFoundError(callable_ref)

        callable_fn = self._callable_registry[callable_ref]

        # Handle both sync and async callables with optional timeout
        if hook.timeout_seconds is not None:
            try:
                if inspect.iscoroutinefunction(callable_fn):
                    await asyncio.wait_for(
                        callable_fn(context), timeout=hook.timeout_seconds
                    )
                else:
                    # NOTE: Sync hook timeout limitation
                    # asyncio.to_thread() runs the sync callable in a thread pool executor.
                    # Thread cancellation in Python is cooperative, not preemptive.
                    # When a timeout occurs:
                    #   - The asyncio.wait_for() will raise TimeoutError immediately
                    #   - BUT the sync code continues running in the background thread
                    #     until it completes naturally or hits an interruptible point
                    # Long-running CPU-bound sync hooks may not respect timeout precisely.
                    # For strict timeout enforcement, prefer async hooks that yield control.
                    await asyncio.wait_for(
                        asyncio.to_thread(callable_fn, context),
                        timeout=hook.timeout_seconds,
                    )
            except TimeoutError:
                raise HookTimeoutError(hook.hook_name, hook.timeout_seconds)
        # Original non-timeout path
        elif inspect.iscoroutinefunction(callable_fn):
            await callable_fn(context)
        else:
            callable_fn(context)


__all__ = [
    "CANONICAL_PHASE_ORDER",
    "HookCallable",
    "RunnerPipeline",
]
