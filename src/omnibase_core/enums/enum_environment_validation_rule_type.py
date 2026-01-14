"""
Environment Validation Rule Type Enumeration.

Defines the types of validation rules that can be applied to
environment-specific configuration values.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEnvironmentValidationRuleType(StrValueHelper, str, Enum):
    """Environment validation rule type enumeration."""

    VALUE_CHECK = "value_check"
    FORMAT = "format"
    RANGE = "range"
    ALLOWED_VALUES = "allowed_values"


__all__ = ["EnumEnvironmentValidationRuleType"]
