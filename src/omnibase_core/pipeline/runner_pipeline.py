# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline runner for executing hooks in canonical phase order."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Coroutine
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.pipeline.exceptions import CallableNotFoundError, HookTimeoutError
from omnibase_core.pipeline.models.model_execution_plan import ModelExecutionPlan
from omnibase_core.pipeline.models.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)

# Type alias for hook callables - they take PipelineContext and return None
# (sync or async)
HookCallable = Callable[["PipelineContext"], None | Coroutine[object, object, None]]


class ModelHookError(BaseModel):
    """
    Represents an error captured during hook execution.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads.

    Note:
        The special ``hook_id`` value ``"[framework]"`` indicates a framework-level
        error during phase execution, not from a specific hook. This can occur in
        the finalize phase if the execution plan itself cannot be accessed or if
        an unexpected error occurs outside of hook invocation.
    """

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # This workaround addresses Pydantic 2.x class identity validation issues where
    # frozen models nested in other models (e.g., in PipelineResult.errors list)
    # fail isinstance() checks across pytest-xdist worker processes.
    # See model_pipeline_hook.py module docstring for detailed explanation.
    # Track: https://github.com/pydantic/pydantic/issues (no specific issue yet)
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    phase: str = Field(
        ...,
        description="The phase where the error occurred",
    )
    hook_id: str = Field(
        ...,
        description="The hook ID that raised the error",
    )
    error_type: str = Field(
        ...,
        description="The type name of the exception",
    )
    error_message: str = Field(
        ...,
        description="The error message",
    )


class PipelineContext(BaseModel):
    """
    Context passed to each hook during pipeline execution.

    The context is shared and mutable across all hooks within a pipeline run,
    allowing hooks to communicate state between each other.

    Thread Safety
    -------------
    **This class is NOT thread-safe.**

    ``PipelineContext`` is intentionally mutable to allow hooks to communicate.
    Each pipeline execution should use its own ``PipelineContext`` instance.
    Do not share contexts across concurrent pipeline executions.

    Pydantic Configuration Note
    ---------------------------
    Unlike other pipeline models (e.g., ``ModelPipelineHook``, ``ModelExecutionPlan``),
    this class does NOT use ``from_attributes=True`` because:

    1. This model is **mutable** (``frozen=False``), not frozen
    2. It is **not nested** inside other Pydantic models during validation
    3. The ``from_attributes=True`` workaround is only needed for frozen models
       that are nested inside other models and validated across pytest-xdist workers

    See ``model_pipeline_hook.py`` module docstring for the full explanation of
    when ``from_attributes=True`` is required.
    """

    # Note: frozen=False is intentional - this context must be mutable for hooks
    # to add data. This does NOT require from_attributes=True (see docstring above).
    model_config = ConfigDict(frozen=False)

    data: dict[str, object] = Field(
        default_factory=dict,
        description="Arbitrary data storage for hooks to share state",
    )


class PipelineResult(BaseModel):
    """
    Result of pipeline execution.

    Contains success status, any captured errors (from continue phases),
    and the final context state.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads. Note that the
    nested ``context`` field may be mutable (PipelineContext), so avoid
    modifying it after the result is created if sharing across threads.
    """

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # This workaround addresses Pydantic 2.x class identity validation issues where
    # frozen models (and models containing frozen nested models like ModelHookError)
    # fail isinstance() checks across pytest-xdist worker processes.
    # See model_pipeline_hook.py module docstring for detailed explanation.
    # Track: https://github.com/pydantic/pydantic/issues (no specific issue yet)
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    success: bool = Field(
        ...,
        description="Whether the pipeline completed without errors",
    )
    errors: list[ModelHookError] = Field(
        default_factory=list,
        description="Errors captured from continue-on-error phases",
    )
    context: PipelineContext | None = Field(
        default=None,
        description="Final context state after pipeline execution",
    )


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
    ModelExecutionPlan               Yes             Frozen Pydantic model (frozen=True)
    ModelPhaseExecutionPlan          Yes             Frozen Pydantic model (frozen=True)
    ModelPipelineHook                Yes             Frozen Pydantic model (frozen=True)
    PipelineContext                  No              Mutable dict for hook communication
    PipelineResult                   Yes             Frozen Pydantic model (frozen=True)
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

    - ``ModelExecutionPlan`` is frozen and can be safely shared across threads
    - ``callable_registry`` dict can be shared IF not modified after runner creation
    - Use ``plan.model_copy()`` if you need isolated plan modifications

    See Also
    --------
    - docs/guides/THREADING.md for comprehensive thread safety guide
    - CLAUDE.md section "Thread Safety" for quick reference
    """

    def __init__(
        self,
        plan: ModelExecutionPlan,
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

    async def run(self) -> PipelineResult:
        """
        Execute the pipeline.

        Returns:
            PipelineResult containing success status, errors, and context

        Raises:
            Exception: Re-raises exceptions from fail-fast phases
            CallableNotFoundError: If a hook's callable_ref is not in the registry
        """
        context = PipelineContext()
        errors: list[ModelHookError] = []
        exception_to_raise: Exception | None = None

        try:
            # Execute all phases except finalize
            for phase in CANONICAL_PHASE_ORDER[:-1]:  # All except finalize
                try:
                    phase_errors = await self._execute_phase(phase, context)
                    errors.extend(phase_errors)
                except Exception as e:
                    # Fail-fast phase raised exception
                    exception_to_raise = e
                    break  # Stop executing phases, but finalize will still run
        finally:
            # Finalize ALWAYS runs
            try:
                finalize_errors = await self._execute_phase("finalize", context)
                errors.extend(finalize_errors)
            except Exception as finalize_exc:
                # This exception handler catches framework-level errors only.
                # Hook execution errors are captured inside _execute_phase with
                # proper hook_id because finalize has fail_fast=False.
                # Framework errors (e.g., plan access failures) have no hook context.
                errors.append(
                    ModelHookError(
                        phase="finalize",
                        hook_id="[framework]",
                        error_type=type(finalize_exc).__name__,
                        error_message=f"Framework error during finalize phase: {finalize_exc}",
                    )
                )

        # Re-raise exception from fail-fast phase if any
        if exception_to_raise is not None:
            raise exception_to_raise

        return PipelineResult(
            success=len(errors) == 0,
            errors=errors,
            context=context,
        )

    async def _execute_phase(
        self,
        phase: PipelinePhase,
        context: PipelineContext,
    ) -> list[ModelHookError]:
        """
        Execute all hooks in a phase.

        Args:
            phase: The phase to execute
            context: The shared pipeline context

        Returns:
            List of errors captured (for continue phases)

        Raises:
            Exception: For fail-fast phases, re-raises the first exception
        """
        hooks = self._plan.get_phase_hooks(phase)
        fail_fast = self._plan.is_phase_fail_fast(phase)
        errors: list[ModelHookError] = []

        for hook in hooks:
            try:
                await self._execute_hook(hook, context)
            except Exception as e:
                if fail_fast:
                    # Re-raise immediately for fail-fast phases
                    raise
                # Capture error and continue for continue phases
                errors.append(
                    ModelHookError(
                        phase=phase,
                        hook_id=hook.hook_id,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                )

        return errors

    async def _execute_hook(
        self,
        hook: ModelPipelineHook,
        context: PipelineContext,
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
                    await asyncio.wait_for(
                        asyncio.to_thread(callable_fn, context),
                        timeout=hook.timeout_seconds,
                    )
            except TimeoutError:
                raise HookTimeoutError(hook.hook_id, hook.timeout_seconds)
        # Original non-timeout path
        elif inspect.iscoroutinefunction(callable_fn):
            await callable_fn(context)
        else:
            callable_fn(context)


# Backwards compatibility alias
PipelineRunner = RunnerPipeline

__all__ = [
    "CANONICAL_PHASE_ORDER",
    "HookCallable",
    "ModelHookError",
    "PipelineContext",
    "PipelineResult",
    "RunnerPipeline",
    "PipelineRunner",
]
