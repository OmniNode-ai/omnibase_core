"""
Result Type Enum.

Strongly typed result type values for configuration and processing.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumResultType(StrValueHelper, str, Enum):
    """
    Strongly typed result type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PARTIAL = "partial"

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
