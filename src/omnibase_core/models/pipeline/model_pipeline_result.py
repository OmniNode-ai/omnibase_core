# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline result model for execution outcomes."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_hook_error import ModelHookError
from omnibase_core.models.pipeline.model_pipeline_context import ModelPipelineContext


class ModelPipelineResult(BaseModel):
    """
    Result of pipeline execution.

    Contains success status, any captured errors (from continue phases),
    and the final context state.

    Thread Safety
    -------------
    **Partially thread-safe with caveats.**

    This model uses ``frozen=True``, making the result itself immutable.
    However, the nested ``context`` field (ModelPipelineContext) is
    intentionally mutable to allow inter-hook communication during pipeline
    execution.

    .. warning:: **Mutable Context in Frozen Result**

        While ``ModelPipelineResult`` is frozen, the ``context`` field contains
        a mutable ``ModelPipelineContext`` object. This creates a thread safety
        boundary:

        - **Safe**: Reading result fields (``success``, ``errors``) across threads
        - **Safe**: Reading ``context.data`` after pipeline completion
        - **Unsafe**: Modifying ``context.data`` after sharing across threads

        If you need to share a pipeline result across threads after execution,
        create a deep copy of the context data::

            import copy

            # Safe way to share result across threads
            result = pipeline.execute()
            frozen_data = copy.deepcopy(result.context.data) if result.context else {}

    Best Practices
    --------------
    1. Treat ``context`` as read-only after pipeline execution completes
    2. Create deep copies if modifications are needed after sharing
    3. Do not pass the same result instance to multiple concurrent consumers
       that may modify ``context.data``
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
    context: ModelPipelineContext | None = Field(
        default=None,
        description=(
            "Final context state after pipeline execution. "
            "WARNING: This field is mutable even though the result is frozen. "
            "Treat as read-only when sharing across threads. See class docstring."
        ),
    )


__all__ = [
    "ModelPipelineResult",
]
