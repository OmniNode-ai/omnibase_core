"""Pipeline context model for hook communication."""

from pydantic import BaseModel, ConfigDict, Field


class ModelPipelineContext(BaseModel):
    """
    Context passed to each hook during pipeline execution.

    The context is shared and mutable across all hooks within a pipeline run,
    allowing hooks to communicate state between each other.

    .. warning:: **Mutable Context Caveat**

        The ``data`` dict passed to hooks is **mutable and shared**. Any hook can
        modify the context, and those changes persist to all subsequent hooks in
        the pipeline. This is intentional for inter-hook communication but requires
        hooks to coordinate their key usage to avoid conflicts.

        Example::

            # Hook A writes to context
            def hook_a(ctx: ModelPipelineContext) -> None:
                ctx.data["result"] = {"status": "processed"}

            # Hook B can read and modify the same data
            def hook_b(ctx: ModelPipelineContext) -> None:
                result = ctx.data.get("result", {})
                result["validated"] = True

    Thread Safety
    -------------
    **This class is NOT thread-safe.**

    ``ModelPipelineContext`` is intentionally mutable to allow hooks to communicate.
    Each pipeline execution should use its own ``ModelPipelineContext`` instance.
    Do not share contexts across concurrent pipeline executions.

    Pydantic Configuration Note
    ---------------------------
    Unlike other pipeline models (e.g., ``ModelPipelineHook``, ``ModelPipelineExecutionPlan``),
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


__all__ = [
    "ModelPipelineContext",
]
