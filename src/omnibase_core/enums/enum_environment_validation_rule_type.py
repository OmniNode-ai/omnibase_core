# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Environment Validation Rule Type Enumeration.

Defines the types of validation rules that can be applied to
environment-specific configuration values.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumEnvironmentValidationRuleType(UtilStrValueHelper, str, Enum):
    """Environment validation rule type enumeration."""

    VALUE_CHECK = "value_check"
    FORMAT = "format"
    RANGE = "range"
    ALLOWED_VALUES = "allowed_values"


__all__ = ["EnumEnvironmentValidationRuleType"]
