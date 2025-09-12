"""
Publisher type enumeration for event publishing selection.
"""

from enum import Enum


class EnumPublisherType(str, Enum):
    """Types of event publishers available."""

    IN_MEMORY = "IN_MEMORY"  # Use in-memory Event Bus
    AUTO = "AUTO"  # Automatically select based on context
    HYBRID = "HYBRID"  # Use hybrid routing between both
