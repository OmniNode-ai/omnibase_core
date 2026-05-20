# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Effect parameter type enumeration.

Defines types for discriminated union in effect parameters.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumEffectParameterType(UtilStrValueHelper, str, Enum):
    """Effect parameter type enumeration for discriminated unions."""

    TARGET_SYSTEM = "target_system"
    OPERATION_MODE = "operation_mode"
    RETRY_SETTING = "retry_setting"
    VALIDATION_RULE = "validation_rule"
    EXTERNAL_REFERENCE = "external_reference"


# Export for use
__all__ = ["EnumEffectParameterType"]
