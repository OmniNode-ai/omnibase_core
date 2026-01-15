"""
Contract data type enumeration.

Defines types for discriminated union in contract data structures.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContractDataType(StrValueHelper, str, Enum):
    """Contract data type enumeration for discriminated unions."""

    SCHEMA_VALUES = "schema_values"
    RAW_VALUES = "raw_values"
    NONE = "none"


# Export for use
__all__ = ["EnumContractDataType"]
