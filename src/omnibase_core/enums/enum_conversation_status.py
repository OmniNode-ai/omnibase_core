"""
Conversation status enumeration for session management.

Defines the status states for conversational RAG sessions
and conversation lifecycle management.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConversationStatus(StrValueHelper, str, Enum):
    """
    Conversation status enumeration for session state management.

    Used to track the lifecycle and state of conversational RAG sessions
    throughout their duration and persistence.
    """

    # Active states
    ACTIVE = "active"
    ONGOING = "ongoing"
    PAUSED = "paused"

    # Completion states
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"

    # Error states
    ERROR = "error"
    FAILED = "failed"
    TIMEOUT = "timeout"

    # Initialization states
    INITIALIZED = "initialized"
    STARTING = "starting"
    READY = "ready"


__all__ = ["EnumConversationStatus"]
