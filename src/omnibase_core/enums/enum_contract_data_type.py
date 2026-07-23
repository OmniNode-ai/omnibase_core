# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract data type enumeration.

Defines types for discriminated union in contract data structures.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractDataType(UtilStrValueHelper, str, Enum):
    """Contract data type enumeration for discriminated unions."""

    SCHEMA_VALUES = "schema_values"
    RAW_VALUES = "raw_values"
    NONE = "none"


# Export for use
__all__ = ["EnumContractDataType"]
