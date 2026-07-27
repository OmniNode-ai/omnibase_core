# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumJsonValueType(UtilStrValueHelper, str, Enum):
    """ONEX-compliant JSON value type enum for validation."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    NULL = "null"


__all__ = ["EnumJsonValueType"]
