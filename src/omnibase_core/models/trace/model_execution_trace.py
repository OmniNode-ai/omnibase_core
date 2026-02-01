"""
Execution Trace Model for Replay Infrastructure.

Defines the ModelExecutionTrace model which captures the complete detailed
timeline of a single execution. Unlike the Manifest (which is a summary),
the Trace provides step-by-step timing and status for replay and debugging.

Relationship to Manifest:
- Manifest = summary of what happened (high-level observability)
- Trace = detailed step-by-step timeline (replay infrastructure)

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Execution Trace infrastructure (OMN-1208)
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.trace.model_execution_trace_step import (
    ModelExecutionTraceStep,
)


class ModelExecutionTrace(BaseModel):
    """
    Complete execution trace for a single run.

    This is the detailed timeline model for the replay infrastructure,
    capturing every step of an execution. It answers "exactly what happened
    and when?" at a granular level.

    Key Concepts:
        - trace_id: Unique identifier for this trace
        - correlation_id: Links related traces across distributed executions
        - dispatch_id: Links to the dispatch that triggered this execution
        - run_id: Links to the specific run instance
        - steps: Ordered list of execution steps with timing

    Attributes:
        trace_id: Unique identifier for this trace
        correlation_id: Correlation ID for distributed tracing
        dispatch_id: Dispatch ID if triggered by a dispatch
        run_id: Run instance ID
        started_at: Execution start timestamp (UTC)
        ended_at: Execution end timestamp (UTC)
        status: Overall execution status
        steps: Ordered list of trace steps

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
        >>> trace = ModelExecutionTrace(
        ...     correlation_id=uuid4(),
        ...     run_id=uuid4(),
        ...     started_at=datetime.now(UTC),
        ...     ended_at=datetime.now(UTC),
        ...     status=EnumExecutionStatus.SUCCESS,
        ... )
        >>> trace.is_successful()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The high-level manifest model
        - :class:`~omnibase_core.models.trace.model_execution_trace_step.ModelExecutionTraceStep`:
          Individual step model

    .. versionadded:: 0.4.0
        Added as part of Execution Trace infrastructure (OMN-1208)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Identity ===

    trace_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this trace",
    )

    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for distributed tracing",
    )

    dispatch_id: UUID | None = Field(
        default=None,
        description="Dispatch ID if triggered by a dispatch",
    )

    run_id: UUID = Field(
        ...,
        description="Run instance ID",
    )

    # === Timing ===

    started_at: datetime = Field(
        ...,
        description="Execution start timestamp (UTC)",
    )

    ended_at: datetime = Field(
        ...,
        description="Execution end timestamp (UTC)",
    )

    # === Status ===

    status: EnumExecutionStatus = Field(
        ...,
        description="Overall execution status",
    )

    # === Steps ===

    steps: list[ModelExecutionTraceStep] = Field(
        default_factory=list,
        description="Ordered list of trace steps",
    )

    # === Validators ===

    @model_validator(mode="after")
    def validate_time_ordering(self) -> "ModelExecutionTrace":
        """Validate that ended_at is not before started_at."""
        if self.ended_at < self.started_at:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"ended_at ({self.ended_at}) cannot be before started_at ({self.started_at})"
            )
        return self

    # === Utility Methods ===

    def get_duration_ms(self) -> float:
        """
        Get the total execution duration in milliseconds.

        Returns:
            Duration in milliseconds from started_at to ended_at
        """
        delta = self.ended_at - self.started_at
        return delta.total_seconds() * 1000.0

    def get_duration_seconds(self) -> float:
        """
        Get the total execution duration in seconds.

        Returns:
            Duration in seconds from started_at to ended_at
        """
        delta = self.ended_at - self.started_at
        return delta.total_seconds()

    def get_failed_steps(self) -> list[ModelExecutionTraceStep]:
        """
        Get all steps that failed.

        Returns:
            List of steps with status "failure"
        """
        return [step for step in self.steps if step.is_failure()]

    def get_successful_steps(self) -> list[ModelExecutionTraceStep]:
        """
        Get all steps that succeeded.

        Returns:
            List of steps with status "success"
        """
        return [step for step in self.steps if step.is_successful()]

    def get_skipped_steps(self) -> list[ModelExecutionTraceStep]:
        """
        Get all steps that were skipped.

        Returns:
            List of steps with status "skipped"
        """
        return [step for step in self.steps if step.is_skipped()]

    def is_successful(self) -> bool:
        """
        Check if the execution was successful.

        Returns:
            True if status is SUCCESS or COMPLETED
        """
        return EnumExecutionStatus.is_successful(self.status)

    def is_failure(self) -> bool:
        """
        Check if the execution failed.

        Returns:
            True if status is FAILED or TIMEOUT
        """
        return EnumExecutionStatus.is_failure(self.status)

    def is_partial(self) -> bool:
        """
        Check if the execution was partially successful.

        Returns:
            True if status is PARTIAL
        """
        return EnumExecutionStatus.is_partial(self.status)

    def is_running(self) -> bool:
        """
        Check if the execution is still running.

        Returns:
            True if status is RUNNING
        """
        return EnumExecutionStatus.is_running(self.status)

    def is_cancelled(self) -> bool:
        """
        Check if the execution was cancelled.

        Returns:
            True if status is CANCELLED
        """
        return EnumExecutionStatus.is_cancelled(self.status)

    def is_terminal(self) -> bool:
        """
        Check if the execution has finished (any terminal state).

        Returns:
            True if status is terminal
        """
        return EnumExecutionStatus.is_terminal(self.status)

    def get_step_count(self) -> int:
        """
        Get the total number of steps.

        Returns:
            Count of steps
        """
        return len(self.steps)

    def get_failure_count(self) -> int:
        """
        Get the number of failed steps.

        Returns:
            Count of failed steps
        """
        return len(self.get_failed_steps())

    def has_steps(self) -> bool:
        """
        Check if there are any steps.

        Returns:
            True if steps list is non-empty
        """
        return len(self.steps) > 0

    def has_failures(self) -> bool:
        """
        Check if there were any failed steps.

        Returns:
            True if any step failed
        """
        return self.get_failure_count() > 0

    def has_dispatch(self) -> bool:
        """
        Check if this trace was triggered by a dispatch.

        Returns:
            True if dispatch_id is set
        """
        return self.dispatch_id is not None

    def get_step_by_id(
        self,
        step_id: str,  # string-id-ok: method param matches step.step_id type
    ) -> ModelExecutionTraceStep | None:
        """
        Get a specific step by its ID.

        Args:
            step_id: The step ID to look up

        Returns:
            The step if found, None otherwise
        """
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_steps_by_kind(self, kind: str) -> list[ModelExecutionTraceStep]:
        """
        Get all steps of a specific kind.

        Args:
            kind: The step kind to filter by (hook, handler, effect_call, invariant_eval)

        Returns:
            List of steps matching the specified kind
        """
        return [step for step in self.steps if step.step_kind == kind]

    def get_total_step_duration_ms(self) -> float:
        """
        Get the sum of all step durations in milliseconds.

        Returns:
            Total duration across all steps
        """
        return sum(step.duration_ms for step in self.steps)

    def get_slowest_step(self) -> ModelExecutionTraceStep | None:
        """
        Get the step with the longest duration.

        Returns:
            The slowest step, or None if no steps
        """
        if not self.steps:
            return None
        return max(self.steps, key=lambda s: s.duration_ms)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"ExecutionTrace({self.trace_id}: "
            f"{self.status.value}, {self.get_step_count()} steps, "
            f"{self.get_duration_ms():.1f}ms)"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelExecutionTrace(trace_id={self.trace_id!r}, "
            f"correlation_id={self.correlation_id!r}, "
            f"run_id={self.run_id!r}, "
            f"status={self.status!r}, "
            f"step_count={self.get_step_count()})"
        )


# Export for use
__all__ = ["ModelExecutionTrace"]
