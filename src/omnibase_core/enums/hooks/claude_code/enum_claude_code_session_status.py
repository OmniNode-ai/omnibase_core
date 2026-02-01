"""Claude Code session status enumeration.

Defines the lifecycle states for a Claude Code session snapshot, tracking
progression from initial event reception through completion or timeout.

Status Transitions:
    ORPHAN -> ACTIVE (on SessionStart received)
    ACTIVE -> ENDED (on SessionEnd received)
    ACTIVE -> TIMED_OUT (on inactivity timeout)
    ORPHAN -> TIMED_OUT (on inactivity timeout without SessionStart)
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumClaudeCodeSessionStatus(StrValueHelper, str, Enum):
    """Status of a Claude Code session snapshot.

    Tracks the lifecycle state of a Claude Code session from initial
    event reception through completion or timeout.

    Status Values:
        ORPHAN - Events received before SessionStarted. This occurs when
            hook events arrive but no SessionStart has been seen yet.
            Common during mid-session reconnection or partial event capture.

        ACTIVE - SessionStarted received, session in progress. Normal
            operational state where events are being processed.

        ENDED - SessionEnded received, session completed normally.
            Terminal state indicating graceful session termination.

        TIMED_OUT - Inactivity timeout triggered. Terminal state indicating
            session was abandoned without explicit SessionEnd.
    """

    ORPHAN = "orphan"
    """Events received before SessionStarted. Mid-session reconnection state."""

    ACTIVE = "active"
    """SessionStarted received, session in progress."""

    ENDED = "ended"
    """SessionEnded received, session completed normally."""

    TIMED_OUT = "timed_out"
    """Inactivity timeout triggered, session abandoned."""

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal session state."""
        return self in {
            EnumClaudeCodeSessionStatus.ENDED,
            EnumClaudeCodeSessionStatus.TIMED_OUT,
        }

    def is_active(self) -> bool:
        """Check if this status represents an active session state."""
        return self == EnumClaudeCodeSessionStatus.ACTIVE


__all__ = ["EnumClaudeCodeSessionStatus"]
