"""
Error Value Type Enum.

Strongly typed enumeration for error value type discriminators.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumErrorValueType(StrValueHelper, str, Enum):
    """
    Strongly typed error value type discriminators.

    Used for discriminated union patterns in error value handling.
    Replaces Union[str, Exception, None] patterns with structured error handling.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    STRING = "string"
    EXCEPTION = "exception"
    NONE = "none"

    @classmethod
    def is_error_present(cls, error_type: EnumErrorValueType) -> bool:
        """Check if the error type represents an actual error."""
        return error_type in {cls.STRING, cls.EXCEPTION}

    @classmethod
    def is_exception_type(cls, error_type: EnumErrorValueType) -> bool:
        """Check if the error type represents an exception object."""
        return error_type == cls.EXCEPTION

    @classmethod
    def is_string_error(cls, error_type: EnumErrorValueType) -> bool:
        """Check if the error type represents a string error message."""
        return error_type == cls.STRING

    @classmethod
    def is_no_error(cls, error_type: EnumErrorValueType) -> bool:
        """Check if the error type represents no error."""
        return error_type == cls.NONE

    @classmethod
    def get_error_types(cls) -> list[EnumErrorValueType]:
        """Get all error value types (excludes NONE)."""
        return [cls.STRING, cls.EXCEPTION]


# Export for use
__all__ = ["EnumErrorValueType"]
