# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Numeric type enumeration.

Enumeration for handling numeric values in validation rules
to replace int | float unions.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumNumericType(UtilStrValueHelper, str, Enum):
    """Numeric type enumeration for validation rules."""

    INTEGER = "integer"
    FLOAT = "float"
    NUMERIC = "numeric"  # Accepts both int and float


# Export the enum
__all__ = ["EnumNumericType"]
