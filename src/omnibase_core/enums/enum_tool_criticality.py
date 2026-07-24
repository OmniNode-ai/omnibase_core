# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tool criticality enumeration."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumToolCriticality(UtilStrValueHelper, str, Enum):
    """
    Tool criticality levels for business impact assessment.

    Defines the business criticality of tools in the system.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


__all__ = ["EnumToolCriticality"]
