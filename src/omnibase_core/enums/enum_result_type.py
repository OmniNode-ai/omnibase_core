"""
Result Type Enum.

Strongly typed result type values for configuration and processing.
"""

from __future__ import annotations

from enum import Enum


class EnumResultType(str, Enum):
    """
    Strongly typed result type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    PARTIAL = "PARTIAL"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_successful(cls, result_type: EnumResultType) -> bool:
        """Check if the result type indicates success."""
        return result_type in {cls.SUCCESS, cls.PARTIAL}

    @classmethod
    def is_error_related(cls, result_type: EnumResultType) -> bool:
        """Check if the result type indicates an error."""
        return result_type == cls.ERROR

    @classmethod
    def is_informational(cls, result_type: EnumResultType) -> bool:
        """Check if the result type is informational."""
        return result_type in {cls.INFO, cls.WARNING}

    @classmethod
    def requires_attention(cls, result_type: EnumResultType) -> bool:
        """Check if the result type requires attention."""
        return result_type in {cls.ERROR, cls.WARNING, cls.PARTIAL}


# Export for use
__all__ = ["EnumResultType"]
