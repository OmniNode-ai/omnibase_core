"""
Validation Level Enumeration for pipeline data integrity.

Defines the validation levels for pipeline data integrity checking
in the metadata processing pipeline.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationLevel(StrValueHelper, str, Enum):
    """Validation levels for pipeline data integrity."""

    BASIC = "BASIC"
    STANDARD = "STANDARD"
    COMPREHENSIVE = "COMPREHENSIVE"
    PARANOID = "PARANOID"
