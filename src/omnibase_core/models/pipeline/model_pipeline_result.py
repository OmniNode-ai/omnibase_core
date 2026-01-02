# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline result model for execution outcomes.

This module contains the PipelineResult class which represents the result
of pipeline execution.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_hook_error import ModelHookError
from omnibase_core.models.pipeline.model_pipeline_context import PipelineContext


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


__all__ = [
    "PipelineResult",
]
