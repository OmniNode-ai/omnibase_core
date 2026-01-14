"""
Regex Flag Type Enum.

Strongly typed enumeration for regex flag type discriminators.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRegexFlagType(StrValueHelper, str, Enum):
    """
    Strongly typed regex flag type discriminators.

    Used for discriminated union patterns in regex flag handling.
    Replaces Union[re.DOTALL, re.IGNORECASE, re.MULTILINE] patterns
    with structured flag handling.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    DOTALL = "dotall"
    IGNORECASE = "ignorecase"
    MULTILINE = "multiline"
    COMBINED = "combined"

    @classmethod
    def is_single_flag(cls, flag_type: EnumRegexFlagType) -> bool:
        """Check if the flag type represents a single regex flag."""
        return flag_type in {cls.DOTALL, cls.IGNORECASE, cls.MULTILINE}

    @classmethod
    def is_combined_flag(cls, flag_type: EnumRegexFlagType) -> bool:
        """Check if the flag type represents combined flags."""
        return flag_type == cls.COMBINED

    @classmethod
    def is_case_sensitive_flag(cls, flag_type: EnumRegexFlagType) -> bool:
        """Check if the flag type affects case sensitivity."""
        return flag_type == cls.IGNORECASE

    @classmethod
    def is_line_boundary_flag(cls, flag_type: EnumRegexFlagType) -> bool:
        """Check if the flag type affects line boundary matching."""
        return flag_type in {cls.DOTALL, cls.MULTILINE}

    @classmethod
    def get_single_flags(cls) -> list[EnumRegexFlagType]:
        """Get all single regex flag types."""
        return [cls.DOTALL, cls.IGNORECASE, cls.MULTILINE]

    @classmethod
    def get_line_boundary_flags(cls) -> list[EnumRegexFlagType]:
        """Get flags that affect line boundary matching."""
        return [cls.DOTALL, cls.MULTILINE]


# Export for use
__all__ = ["EnumRegexFlagType"]
