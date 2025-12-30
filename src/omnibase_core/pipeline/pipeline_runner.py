# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline runner for executing hooks in canonical phase order."""
from __future__ import annotations

import inspect
from collections.abc import Callable, Coroutine

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.pipeline.models.model_execution_plan import ModelExecutionPlan
from omnibase_core.pipeline.models.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)

# Type alias for hook callables - they take PipelineContext and return None
# (sync or async)
HookCallable = Callable[["PipelineContext"], None | Coroutine[object, object, None]]


class ModelHookError(BaseModel):
    """Represents an error captured during hook execution."""

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
    """

    model_config = ConfigDict(frozen=False)  # Mutable for hooks to add data

    data: dict[str, object] = Field(
        default_factory=dict,
        description="Arbitrary data storage for hooks to share state",
    )


class PipelineResult(BaseModel):
    """
    Result of pipeline execution.

    Contains success status, any captured errors (from continue phases),
    and the final context state.
    """

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


class PipelineRunner:
    """
    Executes hooks in the canonical phase order using an execution plan.

    The runner handles:
    - Phase execution order: preflight -> before -> execute -> after -> emit -> finalize
    - Sync and async hook execution
    - Error handling per phase:
        - preflight, before, execute: fail-fast (abort on first error)
        - after, emit, finalize: continue (collect errors, run all hooks)
    - Finalize ALWAYS runs, even if earlier phases raise exceptions
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
            callable_registry: Registry mapping callable_ref strings to actual callables
        """
        self._plan = plan
        self._callable_registry = callable_registry

    async def run(self) -> PipelineResult:
        """
        Execute the pipeline.

        Returns:
            PipelineResult containing success status, errors, and context

        Raises:
            Exception: Re-raises exceptions from fail-fast phases
            KeyError: If a hook's callable_ref is not in the registry
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
                # Even finalize errors should be captured, not raised
                errors.append(
                    ModelHookError(
                        phase="finalize",
                        hook_id="unknown",
                        error_type=type(finalize_exc).__name__,
                        error_message=str(finalize_exc),
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
                else:
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

        Args:
            hook: The hook to execute
            context: The shared pipeline context

        Raises:
            KeyError: If the hook's callable_ref is not in the registry
            Exception: Any exception raised by the hook callable
        """
        callable_ref = hook.callable_ref

        if callable_ref not in self._callable_registry:
            raise KeyError(f"Callable not found in registry: {callable_ref}")

        callable_fn = self._callable_registry[callable_ref]

        # Handle both sync and async callables
        if inspect.iscoroutinefunction(callable_fn):
            await callable_fn(context)
        else:
            callable_fn(context)


__all__ = [
    "CANONICAL_PHASE_ORDER",
    "HookCallable",
    "ModelHookError",
    "PipelineContext",
    "PipelineResult",
    "PipelineRunner",
]
