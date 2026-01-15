"""
Metric Type Enum.

Strongly typed metric type values for infrastructure metrics.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetricType(StrValueHelper, str, Enum):
    """Strongly typed metric type values."""

    PERFORMANCE = "performance"
    SYSTEM = "system"
    BUSINESS = "business"
    CUSTOM = "custom"
    HEALTH = "health"


# Export for use
__all__ = ["EnumMetricType"]
