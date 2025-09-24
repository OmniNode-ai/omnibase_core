"""
Validation level enumeration for categorizing validation depth and quality.

Provides strongly typed validation levels for configuring and reporting
validation behavior across the ONEX architecture.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumValidationLevel(str, Enum):
    """
    Strongly typed validation levels.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for validation level specification.
    """

    # Quality levels (from metadata_node_info.py)
    BASIC = "basic"
    GOOD = "good"
    EXCELLENT = "excellent"

    # Validation strictness levels
    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"

    # Special validation modes
    DISABLED = "disabled"
    WARNING_ONLY = "warning_only"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_quality_levels(cls) -> list[EnumValidationLevel]:
        """Get quality-based validation levels."""
        return [cls.BASIC, cls.GOOD, cls.EXCELLENT]

    @classmethod
    def get_strictness_levels(cls) -> list[EnumValidationLevel]:
        """Get strictness-based validation levels."""
        return [cls.MINIMAL, cls.STANDARD, cls.STRICT, cls.COMPREHENSIVE]

    @classmethod
    def is_quality_level(cls, level: EnumValidationLevel) -> bool:
        """Check if level is a quality-based validation level."""
        return level in cls.get_quality_levels()

    @classmethod
    def is_strictness_level(cls, level: EnumValidationLevel) -> bool:
        """Check if level is a strictness-based validation level."""
        return level in cls.get_strictness_levels()

    @classmethod
    def is_active_validation(cls, level: EnumValidationLevel) -> bool:
        """Check if validation level represents active validation."""
        return level not in {cls.DISABLED, cls.WARNING_ONLY}

    def get_numeric_priority(self) -> int:
        """Get numeric priority for ordering validation levels."""
        priority_map = {
            self.DISABLED: 0,
            self.WARNING_ONLY: 1,
            self.MINIMAL: 2,
            self.BASIC: 3,
            self.STANDARD: 4,
            self.GOOD: 5,
            self.STRICT: 6,
            self.EXCELLENT: 7,
            self.COMPREHENSIVE: 8,
        }
        return priority_map.get(self, 0)


# Export for use
__all__ = ["EnumValidationLevel"]
