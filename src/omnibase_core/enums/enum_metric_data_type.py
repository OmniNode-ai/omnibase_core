"""
Metric Data Type Enum.

Strongly typed metric data type values for data type classification.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetricDataType(StrValueHelper, str, Enum):
    """Strongly typed metric data type values."""

    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"


# Export for use
__all__ = ["EnumMetricDataType"]
