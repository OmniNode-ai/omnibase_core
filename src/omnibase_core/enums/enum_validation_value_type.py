# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Validation value type enumeration.

Enumeration for discriminated union types in validation value objects.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumValidationValueType(UtilStrValueHelper, str, Enum):
    """Validation value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NULL = "null"


# Export the enum
__all__ = ["EnumValidationValueType"]
