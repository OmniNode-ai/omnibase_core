"""Phase execution plan model for pipeline hooks."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)


class ModelPhaseExecutionPlan(BaseModel):
    """
    Execution plan for a single phase.

    The ``fail_fast`` field controls error handling behavior:

    - ``fail_fast=True``: Abort on first error, re-raise exception immediately.
      Used for critical phases where continuing after failure is unsafe.

    - ``fail_fast=False``: Capture errors and continue executing remaining hooks.
      Used for cleanup/notification phases where best-effort execution is preferred.

    Note:
        When using ``BuilderExecutionPlan.build()``, ``fail_fast`` is set
        **explicitly based on phase semantics** (not relying on this default):

        - preflight, before, execute: ``fail_fast=True``
        - after, emit, finalize: ``fail_fast=False``

        The default value of ``True`` is a conservative fallback for manually
        constructed plans where fail-fast is the safer default behavior.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads.

    See Also:
        - ``FAIL_FAST_PHASES`` in ``builder_execution_plan.py`` for phase semantics
        - ``docs/guides/PIPELINE_HOOK_REGISTRY.md`` for detailed documentation
    """

    # TODO(OMN-TBD): [pydantic-v3] Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.  [NEEDS TICKET]
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    phase: PipelinePhase = Field(
        ...,
        description="The phase this plan is for",
    )
    hooks: list[ModelPipelineHook] = Field(
        default_factory=list,
        description="Hooks in topologically sorted execution order",
    )
    fail_fast: bool = Field(
        default=True,
        description=(
            "Whether to abort on first error in this phase. "
            "True = fail-fast (re-raise), False = continue (capture errors). "
            "BuilderExecutionPlan sets this explicitly based on phase semantics."
        ),
    )


__all__ = [
    "ModelPhaseExecutionPlan",
]
