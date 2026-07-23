# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Operation parameter type enumeration.

Defines types for discriminated union in operation parameters.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumOperationParameterType(UtilStrValueHelper, str, Enum):
    """Operation parameter type enumeration for discriminated unions."""

    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    LIST = "list[Any]"
    NESTED = "nested"


# Export for use
__all__ = ["EnumOperationParameterType"]
