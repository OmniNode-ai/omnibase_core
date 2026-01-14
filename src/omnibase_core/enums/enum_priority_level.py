"""
Priority Level Enum

Priority levels for operations and requests across tools.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPriorityLevel(StrValueHelper, str, Enum):
    """
    Priority levels for operations and requests across tools.

    Provides consistent priority classification for resource allocation and scheduling.
    """

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def get_numeric_value(self) -> int:
        """Get numeric value for comparison (higher = more priority)."""
        priority_map = {
            self.LOW: 10,
            self.NORMAL: 20,
            self.HIGH: 30,
            self.CRITICAL: 40,
        }
        return priority_map[self]

    def is_high_priority(self) -> bool:
        """Check if this is high or critical priority."""
        return self in {self.HIGH, self.CRITICAL}

    def requires_immediate_action(self) -> bool:
        """Check if this priority requires immediate action."""
        return self == self.CRITICAL

    def __lt__(self, other: str) -> bool:
        """Enable priority comparison."""
        if isinstance(other, EnumPriorityLevel):
            return self.get_numeric_value() < other.get_numeric_value()
        return super().__lt__(other)

    def __le__(self, other: str) -> bool:
        """Enable priority comparison."""
        if isinstance(other, EnumPriorityLevel):
            return self.get_numeric_value() <= other.get_numeric_value()
        return super().__le__(other)

    def __gt__(self, other: str) -> bool:
        """Enable priority comparison."""
        if isinstance(other, EnumPriorityLevel):
            return self.get_numeric_value() > other.get_numeric_value()
        return super().__gt__(other)

    def __ge__(self, other: str) -> bool:
        """Enable priority comparison."""
        if isinstance(other, EnumPriorityLevel):
            return self.get_numeric_value() >= other.get_numeric_value()
        return super().__ge__(other)
