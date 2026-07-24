# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Metric Type Enum.

Strongly typed metric type values for infrastructure metrics.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumMetricType(UtilStrValueHelper, str, Enum):
    """Strongly typed metric type values."""

    PERFORMANCE = "performance"
    SYSTEM = "system"
    BUSINESS = "business"
    CUSTOM = "custom"
    HEALTH = "health"


# Export for use
__all__ = ["EnumMetricType"]
