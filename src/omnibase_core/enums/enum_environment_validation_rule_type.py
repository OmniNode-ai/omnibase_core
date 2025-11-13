"""
Environment Validation Rule Type Enumeration.

Defines the types of validation rules that can be applied to
environment-specific configuration values.
"""

from enum import Enum


class EnumEnvironmentValidationRuleType(str, Enum):
    """Environment validation rule type enumeration."""

    VALUE_CHECK = "value_check"
    FORMAT = "format"
    RANGE = "range"
    ALLOWED_VALUES = "allowed_values"
