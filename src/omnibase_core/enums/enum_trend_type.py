"""
Trend type enumeration for trend data models.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTrendType(StrValueHelper, str, Enum):
    """
    Enumeration for trend types.

    Provides type-safe options for trend classification.
    """

    METRIC = "metric"
    USAGE = "usage"
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    RESOURCE = "resource"
    CUSTOM = "custom"


# Export for use
__all__ = ["EnumTrendType"]
