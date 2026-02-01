"""
Subscription status enumeration for ONEX event consumers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSubscriptionStatus(StrValueHelper, str, Enum):
    """Status states for event subscriptions."""

    ACTIVE = "ACTIVE"  # Currently receiving and processing events
    PAUSED = "PAUSED"  # Temporarily paused (can be resumed)
    STOPPED = "STOPPED"  # Permanently stopped (must recreate)
    ERROR = "ERROR"  # In error state, not processing
    INITIALIZING = "INITIALIZING"  # Being set up
    CLOSING = "CLOSING"  # Being shut down


__all__ = ["EnumSubscriptionStatus"]
