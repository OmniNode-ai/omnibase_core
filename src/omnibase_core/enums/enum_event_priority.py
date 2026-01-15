"""
Event priority enumeration for ONEX event publishing.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEventPriority(StrValueHelper, str, Enum):
    """Priority levels for event processing."""

    CRITICAL = "critical"  # Process immediately, highest priority
    HIGH = "high"  # Process with high priority
    NORMAL = "normal"  # Standard processing priority
    LOW = "low"  # Process when resources available
    DEFERRED = "deferred"  # Process in background, lowest priority


__all__ = ["EnumEventPriority"]
