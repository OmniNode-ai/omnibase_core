"""
Execution Trace Step Model.

Defines the ModelExecutionTraceStep model which represents a single step
within an execution trace. Each step captures detailed timing and status
information for hooks, handlers, effect calls, or invariant evaluations.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Execution Trace infrastructure (OMN-1208)
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelExecutionTraceStep(BaseModel):
    """
    Single step within an execution trace.

    Each step represents a discrete unit of work during execution, such as
    a hook invocation, handler execution, effect call, or invariant evaluation.
    Steps form the detailed timeline of what happened during a single execution.

    Attributes:
        step_id: Unique identifier for this step
        step_kind: Type of step (hook, handler, effect_call, invariant_eval)
        name: Human-readable name (hook_id, handler_id, etc.)
        start_ts: Start timestamp (UTC)
        end_ts: End timestamp (UTC)
        duration_ms: Duration in milliseconds
        status: Step execution status (success, failure, skipped)
        error_summary: Bounded error summary if failed (max 500 chars)
        manifest_ref: Reference to associated manifest if applicable
        effect_record_ref: Reference to effect record if applicable
        invariant_result_ref: Reference to invariant result if applicable

    Example:
        >>> from datetime import datetime, UTC
        >>> step = ModelExecutionTraceStep(
        ...     step_id="step-001",
        ...     step_kind="handler",
        ...     name="handler_transform",
        ...     start_ts=datetime.now(UTC),
        ...     end_ts=datetime.now(UTC),
        ...     duration_ms=45.2,
        ...     status="success",
        ... )
        >>> step.is_successful()
        True

    See Also:
        - :class:`~omnibase_core.models.trace.model_execution_trace.ModelExecutionTrace`:
          The parent trace model

    .. versionadded:: 0.4.0
        Added as part of Execution Trace infrastructure (OMN-1208)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Required Fields ===

    step_id: str = Field(  # string-id-ok: user-facing identifier
        ...,
        min_length=1,
        description="Unique identifier for this step",
    )

    step_kind: Literal["hook", "handler", "effect_call", "invariant_eval"] = Field(
        ...,
        description="Type of step being traced",
    )

    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name (hook_id, handler_id, etc.)",
    )

    start_ts: datetime = Field(
        ...,
        description="Start timestamp (UTC)",
    )

    end_ts: datetime = Field(
        ...,
        description="End timestamp (UTC)",
    )

    duration_ms: float = Field(
        ...,
        ge=0.0,
        description="Duration in milliseconds",
    )

    status: Literal["success", "failure", "skipped"] = Field(
        ...,
        description="Step execution status",
    )

    # === Optional Fields ===

    error_summary: str | None = Field(
        default=None,
        max_length=500,
        description="Bounded error summary if failed (max 500 chars)",
    )

    manifest_ref: UUID | None = Field(
        default=None,
        description="Reference to associated manifest if applicable",
    )

    effect_record_ref: UUID | None = Field(
        default=None,
        description="Reference to effect record if applicable",
    )

    invariant_result_ref: UUID | None = Field(
        default=None,
        description="Reference to invariant result if applicable",
    )

    # === Validators ===

    @field_validator("error_summary", mode="before")
    @classmethod
    def truncate_error_summary(cls, v: str | None) -> str | None:
        """Truncate error_summary to max 500 characters if needed.

        Args:
            v: The error summary string or None.

        Returns:
            The (possibly truncated) error summary string, or None.

        Raises:
            ValueError: If the value is not a string.
        """
        if v is None:
            return None
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"error_summary must be a string, got {type(v).__name__}")
        if len(v) > 500:
            return v[:497] + "..."
        return v

    @model_validator(mode="after")
    def validate_time_ordering(self) -> "ModelExecutionTraceStep":
        """Validate that end_ts is not before start_ts."""
        if self.end_ts < self.start_ts:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"end_ts ({self.end_ts}) cannot be before start_ts ({self.start_ts})"
            )
        return self

    # === Utility Methods ===

    def is_successful(self) -> bool:
        """
        Check if the step executed successfully.

        Returns:
            True if status is success
        """
        return self.status == "success"

    def is_failure(self) -> bool:
        """
        Check if the step failed.

        Returns:
            True if status is failure
        """
        return self.status == "failure"

    def is_skipped(self) -> bool:
        """
        Check if the step was skipped.

        Returns:
            True if status is skipped
        """
        return self.status == "skipped"

    def has_error(self) -> bool:
        """
        Check if there is an error summary.

        Returns:
            True if error_summary is set
        """
        return self.error_summary is not None

    def has_manifest_ref(self) -> bool:
        """
        Check if there is a manifest reference.

        Returns:
            True if manifest_ref is set
        """
        return self.manifest_ref is not None

    def has_effect_record_ref(self) -> bool:
        """
        Check if there is an effect record reference.

        Returns:
            True if effect_record_ref is set
        """
        return self.effect_record_ref is not None

    def has_invariant_result_ref(self) -> bool:
        """
        Check if there is an invariant result reference.

        Returns:
            True if invariant_result_ref is set
        """
        return self.invariant_result_ref is not None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"TraceStep({self.name}@{self.step_kind}: "
            f"{self.status}, {self.duration_ms:.1f}ms)"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelExecutionTraceStep(step_id={self.step_id!r}, "
            f"step_kind={self.step_kind!r}, "
            f"name={self.name!r}, "
            f"status={self.status!r}, "
            f"duration_ms={self.duration_ms!r})"
        )


# Export for use
__all__ = ["ModelExecutionTraceStep"]
