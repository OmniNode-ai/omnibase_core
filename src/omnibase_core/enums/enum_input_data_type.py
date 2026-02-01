"""
Input data type enum for discriminated union.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumInputDataType(StrValueHelper, str, Enum):
    """Types of input data structures."""

    STRUCTURED = "structured"
    PRIMITIVE = "primitive"
    MIXED = "mixed"


__all__ = ["EnumInputDataType"]
