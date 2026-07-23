# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tool Health Status Enums.

Health status values for tool monitoring.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumToolHealthStatus(UtilStrValueHelper, str, Enum):
    """Tool health status values for monitoring and reporting."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


__all__ = ["EnumToolHealthStatus"]
