"""Hook error model for pipeline execution."""

from pydantic import BaseModel, ConfigDict, Field


class ModelHookError(BaseModel):
    """
    Represents an error captured during hook execution.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads.

    Note:
        The special ``hook_name`` value ``"[framework]"`` indicates a framework-level
        error during phase execution, not from a specific hook. This can occur in
        the finalize phase if the execution plan itself cannot be accessed or if
        an unexpected error occurs outside of hook invocation.
    """

    # TODO(OMN-TBD): [pydantic-v3] Re-evaluate from_attributes=True when Pydantic v3 is released.
    # This workaround addresses Pydantic 2.x class identity validation issues where
    # frozen models nested in other models (e.g., in ModelPipelineResult.errors list)
    # fail isinstance() checks across pytest-xdist worker processes.
    # See model_pipeline_hook.py module docstring for detailed explanation.
    # Track: https://github.com/pydantic/pydantic/issues (no specific issue yet)  [NEEDS TICKET]
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    phase: str = Field(
        ...,
        description="The phase where the error occurred",
    )
    hook_name: str = Field(
        ...,
        description="The hook name that raised the error",
    )
    error_type: str = Field(
        ...,
        description="The type name of the exception",
    )
    error_message: str = Field(
        ...,
        description="The error message",
    )


__all__ = [
    "ModelHookError",
]
