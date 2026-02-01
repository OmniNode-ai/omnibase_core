"""
Hook Trace Model for Execution Manifest.

Defines the ModelHookTrace model which captures the execution trace for a
single hook invocation during pipeline execution. This answers "what actually
executed, and what happened?".

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase


class ModelHookTrace(BaseModel):
    """
    Execution trace for a single hook invocation.

    This model captures what actually happened when a hook executed,
    including timing, status, and any errors. One activation entry may
    correspond to zero, one, or multiple hook traces.

    Note: Hook trace is execution-level, not decision-level. For
    decision-level information, see ModelCapabilityActivation.

    Attributes:
        hook_id: Unique identifier for this hook execution
        capability_id: Associated capability if applicable
        handler_id: The handler that executed
        phase: Execution phase when hook ran
        status: Execution status (SUCCESS, FAILED, SKIPPED, etc.)
        started_at: Start timestamp (UTC)
        ended_at: End timestamp (UTC) if completed
        duration_ms: Duration in milliseconds
        error_message: Error message if failed
        error_code: Error code if failed
        skip_reason: Reason if skipped
        retry_count: Number of retries attempted
        input_hash: Hash of input data for correlation
        output_hash: Hash of output data for correlation
        metadata: Additional metadata about the execution

    Status Classification:
        The status can be checked using utility methods:

        - ``is_success()``: True for SUCCESS or COMPLETED
        - ``is_failure()``: True for FAILED or TIMEOUT
        - ``is_skipped()``: True for SKIPPED
        - ``is_cancelled()``: True for CANCELLED
        - ``is_running()``: True for RUNNING

        Note that CANCELLED is neither a success nor a failure - it represents
        an intentional termination. Use ``is_cancelled()`` to check for this
        specific status.

    Example:
        >>> from datetime import datetime, UTC
        >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
        >>> from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
        >>> trace = ModelHookTrace(
        ...     hook_id="hook-001",
        ...     handler_id="handler_transform",
        ...     phase=EnumHandlerExecutionPhase.EXECUTE,
        ...     status=EnumExecutionStatus.SUCCESS,
        ...     started_at=datetime.now(UTC),
        ...     duration_ms=45.2,
        ... )
        >>> trace.is_success()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model
        - :class:`~omnibase_core.enums.enum_execution_status.EnumExecutionStatus`:
          The status enum

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Required Fields ===

    hook_id: str = Field(  # string-id-ok: user-facing identifier
        ...,
        min_length=1,
        description="Unique identifier for this hook execution",
    )

    handler_id: str = Field(
        ...,
        min_length=1,
        description="The handler that executed",
    )

    phase: EnumHandlerExecutionPhase = Field(
        ...,
        description="Execution phase when hook ran",
    )

    status: EnumExecutionStatus = Field(
        ...,
        description="Execution status",
    )

    started_at: datetime = Field(
        ...,
        description="Start timestamp (UTC)",
    )

    # === Optional Fields ===

    capability_id: str | None = Field(  # string-id-ok: user-facing identifier
        default=None,
        description="Associated capability if applicable",
    )

    ended_at: datetime | None = Field(
        default=None,
        description="End timestamp (UTC) if completed",
    )

    duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Duration in milliseconds",
    )

    # === Error Context ===

    error_message: str | None = Field(
        default=None,
        description="Error message if failed",
    )

    error_code: str | None = Field(
        default=None,
        description="Error code if failed",
    )

    skip_reason: str | None = Field(
        default=None,
        description="Reason if skipped",
    )

    # === Execution Context ===

    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries attempted",
    )

    input_hash: str | None = Field(
        default=None,
        description="Hash of input data for correlation",
    )

    output_hash: str | None = Field(
        default=None,
        description="Hash of output data for correlation",
    )

    metadata: dict[str, str | int | float | bool | None] | None = Field(
        default=None,
        description="Additional metadata about the execution",
    )

    # === Utility Methods ===

    def is_success(self) -> bool:
        """
        Check if the hook executed successfully.

        Returns:
            True if status is SUCCESS or COMPLETED
        """
        return EnumExecutionStatus.is_successful(self.status)

    def is_failure(self) -> bool:
        """
        Check if the hook failed.

        Returns:
            True if status is FAILED or TIMEOUT
        """
        return EnumExecutionStatus.is_failure(self.status)

    def is_skipped(self) -> bool:
        """
        Check if the hook was skipped.

        Returns:
            True if status is SKIPPED
        """
        return EnumExecutionStatus.is_skipped(self.status)

    def is_complete(self) -> bool:
        """
        Check if the hook execution has completed.

        Returns:
            True if ended_at is set
        """
        return self.ended_at is not None

    def is_running(self) -> bool:
        """
        Check if the hook is still running.

        Returns:
            True if status is RUNNING
        """
        return EnumExecutionStatus.is_running(self.status)

    def is_cancelled(self) -> bool:
        """
        Check if the hook was cancelled.

        Returns:
            True if status is CANCELLED
        """
        return EnumExecutionStatus.is_cancelled(self.status)

    def has_error(self) -> bool:
        """
        Check if there is an error message.

        Returns:
            True if error_message is set
        """
        return self.error_message is not None

    def was_retried(self) -> bool:
        """
        Check if the hook was retried.

        Returns:
            True if retry_count > 0
        """
        return self.retry_count > 0

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"HookTrace({self.handler_id}@{self.phase.value}: "
            f"{self.status.value}, {self.duration_ms:.1f}ms)"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelHookTrace(hook_id={self.hook_id!r}, "
            f"handler_id={self.handler_id!r}, "
            f"phase={self.phase!r}, "
            f"status={self.status!r}, "
            f"duration_ms={self.duration_ms!r})"
        )


# Export for use
__all__ = ["ModelHookTrace"]
