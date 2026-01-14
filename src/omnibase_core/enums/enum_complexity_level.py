"""
Complexity Level Enum.

Defines complexity levels for functions and operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumComplexityLevel(StrValueHelper, str, Enum):
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
    CRITICAL = "critical"
    UNKNOWN = "unknown"

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
            cls.CRITICAL: 11,
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
        return level in {cls.HIGH, cls.COMPLEX, cls.ADVANCED, cls.EXPERT, cls.CRITICAL}


# Export for use
__all__ = ["EnumComplexityLevel"]
