"""Claude Code session outcome model.

Represents the outcome of a Claude Code session for the feedback loop.
Emitted by omniclaude SessionEnd/Stop hook and consumed by omniintelligence
for pattern learning and session analysis.

This is a pure data model with no side effects.

.. versionadded:: 0.4.1
    Added as part of Claude Code feedback loop infrastructure (OMN-1762)
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_outcome import (
    EnumClaudeCodeSessionOutcome,
)
from omnibase_core.models.services.model_error_details import ModelErrorDetails


class ModelClaudeCodeSessionOutcome(BaseModel):
    """Outcome data for a completed Claude Code session.

    Captures the final outcome of a Claude Code session, including success/failure
    classification and optional error details. This model is emitted by the
    SessionEnd/Stop hook in omniclaude and consumed by omniintelligence for
    pattern learning, success rate tracking, and failure analysis.

    Attributes:
        session_id: Unique identifier for the Claude Code session.
        outcome: Classification of how the session ended (SUCCESS, FAILED,
            ABANDONED, or UNKNOWN).
        error: Structured error details if the outcome is FAILED. Contains
            error code, message, component information, and recovery suggestions.
        correlation_id: Optional identifier for distributed tracing, linking
            this outcome to related events across services.

    Example:
        Successful session outcome::

            >>> from uuid import uuid4
            >>> outcome = ModelClaudeCodeSessionOutcome(
            ...     session_id=uuid4(),
            ...     outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
            ... )
            >>> outcome.is_successful()
            True

        Failed session with error details::

            >>> from omnibase_core.models.services import ModelErrorDetails
            >>> error = ModelErrorDetails(
            ...     error_code="TOOL_EXECUTION_FAILED",
            ...     error_type="runtime",
            ...     error_message="File not found during edit operation",
            ...     component="Edit",
            ... )
            >>> outcome = ModelClaudeCodeSessionOutcome(
            ...     session_id=uuid4(),
            ...     outcome=EnumClaudeCodeSessionOutcome.FAILED,
            ...     error=error,
            ... )
            >>> outcome.is_failure()
            True

    Note:
        This model is frozen (immutable) after creation. The error field
        uses ModelErrorDetails for structured error information rather than
        a plain string, enabling richer error context and recovery guidance.

    .. versionadded:: 0.4.1
        Added as part of Claude Code feedback loop infrastructure (OMN-1762)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    session_id: UUID = Field(
        ...,
        description="Unique identifier for the Claude Code session",
    )

    outcome: EnumClaudeCodeSessionOutcome = Field(
        ...,
        description="Classification of how the session ended",
    )

    # NOTE(OMN-1762): ModelErrorDetails is generic but type parameter unused for session error context.
    error: ModelErrorDetails | None = Field(  # type: ignore[type-arg]
        default=None,
        description="Error details if outcome is FAILED",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for distributed tracing",
    )

    def is_successful(self) -> bool:
        """Check if this outcome represents a successful session."""
        return self.outcome.is_successful()

    def is_failure(self) -> bool:
        """Check if this outcome represents a failed or abandoned session."""
        return self.outcome.is_failure()

    def __str__(self) -> str:
        """Return human-readable string representation.

        Example:
            >>> str(outcome)
            'SessionOutcome(abc12345...: outcome=success)'
        """
        session_display = str(self.session_id)[:8] + "..."
        error_info = f", error={self.error.error_code}" if self.error else ""
        return f"SessionOutcome({session_display}: outcome={self.outcome}{error_info})"

    def __repr__(self) -> str:
        """Return detailed representation for debugging.

        Example:
            >>> repr(outcome)
            "ModelClaudeCodeSessionOutcome(session_id=UUID('...'), outcome=<...>)"
        """
        return (
            f"ModelClaudeCodeSessionOutcome(session_id={self.session_id!r}, "
            f"outcome={self.outcome!r}, "
            f"error={self.error!r}, "
            f"correlation_id={self.correlation_id!r})"
        )


__all__ = ["ModelClaudeCodeSessionOutcome"]
