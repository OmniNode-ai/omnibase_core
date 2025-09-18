"""
Priority Enumeration

Universal priority levels for ONEX architecture.
"""

from enum import Enum


class EnumPriority(str, Enum):
    """
    Universal priority levels.

    String-based enum for prioritization across all ONEX systems.
    Can be used for workflows, requests, tasks, jobs, or any prioritization need.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    def get_numeric_priority(self) -> int:
        """Get numeric priority value for sorting (higher = more priority)."""
        priority_values = {
            self.LOW: 1,
            self.NORMAL: 2,
            self.HIGH: 3,
            self.URGENT: 4,
        }
        return priority_values[self]

    def get_timeout_multiplier(self) -> float:
        """Get timeout multiplier based on priority."""
        multipliers = {
            self.LOW: 0.5,  # Half timeout for low priority
            self.NORMAL: 1.0,  # Normal timeout
            self.HIGH: 1.5,  # 50% longer timeout
            self.URGENT: 2.0,  # Double timeout for urgent
        }
        return multipliers[self]

    def can_preempt(self, other_priority: "EnumPriority") -> bool:
        """Check if this priority can preempt another priority."""
        return self.get_numeric_priority() > other_priority.get_numeric_priority()

    @classmethod
    def get_default(cls) -> "EnumPriority":
        """Get default priority level."""
        return cls.NORMAL
