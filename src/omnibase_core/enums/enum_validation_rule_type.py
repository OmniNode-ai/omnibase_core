"""
Validation Rule Type Enumeration.

Defines the types of validation rules that can be applied to
configuration keys using various validation strategies.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationRuleType(StrValueHelper, str, Enum):
    """Validation rule type enumeration."""

    REGEX = "regex"
    JSON_SCHEMA = "json_schema"
    RANGE = "range"
    ENUM = "enum"


__all__ = ["EnumValidationRuleType"]
