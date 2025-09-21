"""
Metric Data Type Enum.

Strongly typed metric data type values for data type classification.
"""

from __future__ import annotations

from enum import Enum


class EnumMetricDataType(str, Enum):
    """Strongly typed metric data type values."""

    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"


# Export for use
__all__ = ["EnumMetricDataType"]