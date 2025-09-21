"""
Complexity Level Enum.

Defines complexity levels for functions and operations.
"""

from __future__ import annotations

from enum import Enum


class EnumComplexityLevel(str, Enum):
    """Complexity levels for functions and operations."""

    SIMPLE = "simple"
    BASIC = "basic"
    LOW = "low"
    MEDIUM = "medium"
    MODERATE = "moderate"
    HIGH = "high"
    COMPLEX = "complex"
    ADVANCED = "advanced"
    EXPERT = "expert"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_numeric_value(cls, level: EnumComplexityLevel) -> int:
        """Get numeric representation of complexity level (1-10)."""
        mapping = {
            cls.SIMPLE: 1,
            cls.BASIC: 2,
            cls.LOW: 3,
            cls.MEDIUM: 5,
            cls.MODERATE: 6,
            cls.HIGH: 7,
            cls.COMPLEX: 8,
            cls.ADVANCED: 9,
            cls.EXPERT: 10,
            cls.UNKNOWN: 5,  # Default to medium
        }
        return mapping.get(level, 5)

    @classmethod
    def is_simple(cls, level: EnumComplexityLevel) -> bool:
        """Check if complexity level is considered simple."""
        return level in {cls.SIMPLE, cls.BASIC, cls.LOW}

    @classmethod
    def is_complex(cls, level: EnumComplexityLevel) -> bool:
        """Check if complexity level is considered complex."""
        return level in {cls.HIGH, cls.COMPLEX, cls.ADVANCED, cls.EXPERT}


# Export for use
__all__ = ["EnumComplexityLevel"]