"""
Time Unit Enumeration.

Time unit enumeration for flexible time representation.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


@unique
class EnumTimeUnit(str, Enum):
    """Time unit enumeration for flexible time representation."""

    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"
    DAYS = "d"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        # Class-level mapping for maintainability - if enum values change,
        # this mapping will need to be updated accordingly
        return self._get_display_names()[self]

    def to_milliseconds_multiplier(self) -> int:
        """Get multiplier to convert this unit to milliseconds."""
        # Class-level mapping for maintainability - if enum values change,
        # this mapping will need to be updated accordingly
        return self._get_millisecond_multipliers()[self]

    @classmethod
    def _get_display_names(cls) -> dict[EnumTimeUnit, str]:
        """Get display name mapping. Update this when adding new enum values."""
        return {
            cls.MILLISECONDS: "Milliseconds",
            cls.SECONDS: "Seconds",
            cls.MINUTES: "Minutes",
            cls.HOURS: "Hours",
            cls.DAYS: "Days",
        }

    @classmethod
    def _get_millisecond_multipliers(cls) -> dict[EnumTimeUnit, int]:
        """Get millisecond multiplier mapping. Update this when adding new enum values."""
        return {
            cls.MILLISECONDS: 1,
            cls.SECONDS: 1000,
            cls.MINUTES: 60 * 1000,
            cls.HOURS: 60 * 60 * 1000,
            cls.DAYS: 24 * 60 * 60 * 1000,
        }

    @classmethod
    def validate_completeness(cls) -> None:
        """Validate that all enum members have required mappings."""
        all_members = set(cls)
        display_keys = set(cls._get_display_names().keys())
        multiplier_keys = set(cls._get_millisecond_multipliers().keys())

        if display_keys != all_members:
            from omnibase_core.exceptions.onex_error import OnexError

            missing = all_members - display_keys
            raise OnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                f"Missing display names for: {missing}",
            )

        if multiplier_keys != all_members:
            from omnibase_core.exceptions.onex_error import OnexError

            missing = all_members - multiplier_keys
            raise OnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                f"Missing multipliers for: {missing}",
            )


# Validate mappings at module level - this will raise an error if mappings are incomplete
EnumTimeUnit.validate_completeness()


# Export for use
__all__ = ["EnumTimeUnit"]
