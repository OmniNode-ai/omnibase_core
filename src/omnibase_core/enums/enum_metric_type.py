"""
Metric Type Enum.

Strongly typed metric type values for infrastructure metrics.
"""

from __future__ import annotations

from enum import Enum


class EnumMetricType(str, Enum):
    """Strongly typed metric type values."""

    PERFORMANCE = "PERFORMANCE"
    SYSTEM = "SYSTEM"
    BUSINESS = "BUSINESS"
    CUSTOM = "CUSTOM"
    HEALTH = "HEALTH"


# Export for use
__all__ = ["EnumMetricType"]
