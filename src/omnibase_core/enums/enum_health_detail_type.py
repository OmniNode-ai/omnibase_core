# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Health Detail Type Enum.

Canonical enum for health detail types used in component health monitoring.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumHealthDetailType(UtilStrValueHelper, str, Enum):
    """Canonical health detail types for component monitoring."""

    INFO = "info"
    METRIC = "metric"
    WARNING = "warning"
    ERROR = "error"
    DIAGNOSTIC = "diagnostic"


__all__ = ["EnumHealthDetailType"]
