"""
Event priority enumeration for ONEX event publishing.
"""

from enum import Enum


class EnumEventPriority(str, Enum):
    """Priority levels for event processing."""

    CRITICAL = "CRITICAL"  # Process immediately, highest priority
    HIGH = "HIGH"  # Process with high priority
    NORMAL = "NORMAL"  # Standard processing priority
    LOW = "LOW"  # Process when resources available
    DEFERRED = "DEFERRED"  # Process in background, lowest priority
