"""Claude Code session outcome enumeration.

Classifies how a Claude Code session ended, providing semantic meaning
for session termination beyond just the status lifecycle state.

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumClaudeCodeSessionOutcome(StrValueHelper, str, Enum):
    """Outcome classification for a completed Claude Code session.

    Provides semantic classification of how a session ended, enabling
    analysis of session success rates and failure patterns.

    Outcome Values:
        SUCCESS - Session completed with successful task execution.
            The user's request was fulfilled and the session ended normally.

        FAILED - Session ended with task failure or error.
            The session terminated but the intended task was not completed
            due to errors, validation failures, or other blocking issues.

        ABANDONED - Session was abandoned without completion.
            The user terminated the session before task completion,
            or the session timed out due to inactivity.

        UNKNOWN - Outcome could not be determined.
            Used when session metadata is incomplete or when the outcome
            cannot be reliably classified from available data.
    """

    SUCCESS = "success"
    """Session completed with successful task execution."""

    FAILED = "failed"
    """Session ended with task failure or error."""

    ABANDONED = "abandoned"
    """Session was abandoned without completion."""

    UNKNOWN = "unknown"
    """Outcome could not be determined from available data."""

    def is_terminal(self) -> bool:
        """Check if this outcome represents a terminal classification.

        All outcomes except UNKNOWN are considered terminal since they
        represent definitive session end states.
        """
        return self != EnumClaudeCodeSessionOutcome.UNKNOWN

    def is_successful(self) -> bool:
        """Check if this outcome represents a successful session."""
        return self == EnumClaudeCodeSessionOutcome.SUCCESS

    def is_failure(self) -> bool:
        """Check if this outcome represents a failed or abandoned session."""
        return self in {
            EnumClaudeCodeSessionOutcome.FAILED,
            EnumClaudeCodeSessionOutcome.ABANDONED,
        }


__all__ = ["EnumClaudeCodeSessionOutcome"]
