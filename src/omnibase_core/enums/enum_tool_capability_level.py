# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumToolCapabilityLevel(UtilStrValueHelper, str, Enum):
    """Tool capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"


__all__ = ["EnumToolCapabilityLevel"]
