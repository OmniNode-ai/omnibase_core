from __future__ import annotations

"""
Connection state enumeration for connection lifecycle tracking.

Provides strongly typed connection state values for monitoring connection status.
Follows ONEX one-enum-per-file naming conventions.
"""


from enum import Enum, unique


@unique
class EnumConnectionState(str, Enum):
    """
    Strongly typed connection state for lifecycle tracking.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    TIMEOUT = "timeout"
    CLOSING = "closing"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_stable(cls, state: EnumConnectionState) -> bool:
        """Check if the connection state is stable."""
        return state in {cls.CONNECTED, cls.DISCONNECTED}

    @classmethod
    def is_transitional(cls, state: EnumConnectionState) -> bool:
        """Check if the connection state is transitional."""
        return state in {cls.CONNECTING, cls.RECONNECTING, cls.CLOSING}

    @classmethod
    def is_error_state(cls, state: EnumConnectionState) -> bool:
        """Check if the connection state represents an error."""
        return state in {cls.ERROR, cls.TIMEOUT}

    @classmethod
    def can_send_data(cls, state: EnumConnectionState) -> bool:
        """Check if data can be sent in this connection state."""
        return state == cls.CONNECTED


# Export for use
__all__ = ["EnumConnectionState"]
