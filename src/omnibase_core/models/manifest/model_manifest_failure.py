"""
Manifest Failure Model for Execution Manifest.

Defines the ModelManifestFailure model which captures details of failures
that occurred during pipeline execution.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase


class ModelManifestFailure(BaseModel):
    """
    Details of a failure during pipeline execution.

    This model captures information about failures that occurred during
    execution, providing context for debugging and error reporting.

    Attributes:
        failed_at: Timestamp when the failure occurred
        phase: Execution phase where failure occurred (if applicable)
        handler_id: Handler that failed (if applicable)
        error_code: Error code identifying the type of failure
        error_message: Human-readable error message
        stack_trace: Optional stack trace for debugging
        recoverable: Whether the failure is potentially recoverable

    Example:
        >>> from datetime import datetime, UTC
        >>> failure = ModelManifestFailure(
        ...     failed_at=datetime.now(UTC),
        ...     error_code="HANDLER_TIMEOUT",
        ...     error_message="Handler exceeded timeout of 30 seconds",
        ...     handler_id="handler_transform",
        ...     recoverable=True,
        ... )
        >>> failure.is_recoverable()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model

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

    failed_at: datetime = Field(
        ...,
        description="Timestamp when the failure occurred (UTC)",
    )

    error_code: str = Field(
        ...,
        min_length=1,
        description="Error code identifying the type of failure",
    )

    error_message: str = Field(
        ...,
        min_length=1,
        description="Human-readable error message",
    )

    # === Optional Context Fields ===

    phase: EnumHandlerExecutionPhase | None = Field(
        default=None,
        description="Execution phase where failure occurred",
    )

    handler_id: str | None = Field(
        default=None,
        description="Handler that failed (if applicable)",
    )

    stack_trace: str | None = Field(
        default=None,
        description="Stack trace for debugging",
    )

    recoverable: bool = Field(
        default=False,
        description="Whether the failure is potentially recoverable",
    )

    # === Utility Methods ===

    def is_recoverable(self) -> bool:
        """
        Check if the failure is potentially recoverable.

        Returns:
            True if the failure is marked as recoverable
        """
        return self.recoverable

    def has_handler(self) -> bool:
        """
        Check if a handler was associated with the failure.

        Returns:
            True if handler_id is set
        """
        return self.handler_id is not None

    def has_phase(self) -> bool:
        """
        Check if a phase was associated with the failure.

        Returns:
            True if phase is set
        """
        return self.phase is not None

    def has_stack_trace(self) -> bool:
        """
        Check if a stack trace is available.

        Returns:
            True if stack_trace is set
        """
        return self.stack_trace is not None

    def get_summary(self) -> str:
        """
        Get a brief summary of the failure.

        Returns:
            Summary string with error code and message
        """
        return f"[{self.error_code}] {self.error_message}"

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        context = ""
        if self.handler_id:
            context = f" in {self.handler_id}"
        elif self.phase:
            context = f" during {self.phase.value}"
        return f"Failure({self.error_code}{context}: {self.error_message})"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelManifestFailure(error_code={self.error_code!r}, "
            f"error_message={self.error_message!r}, "
            f"handler_id={self.handler_id!r}, "
            f"phase={self.phase!r}, "
            f"recoverable={self.recoverable!r})"
        )


# Export for use
__all__ = ["ModelManifestFailure"]
