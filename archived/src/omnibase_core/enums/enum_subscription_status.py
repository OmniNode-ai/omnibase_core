"""
Subscription status enumeration for ONEX event consumers.
"""

from enum import Enum


class EnumSubscriptionStatus(str, Enum):
    """Status states for event subscriptions."""

    ACTIVE = "ACTIVE"  # Currently receiving and processing events
    PAUSED = "PAUSED"  # Temporarily paused (can be resumed)
    STOPPED = "STOPPED"  # Permanently stopped (must recreate)
    ERROR = "ERROR"  # In error state, not processing
    INITIALIZING = "INITIALIZING"  # Being set up
    CLOSING = "CLOSING"  # Being shut down
