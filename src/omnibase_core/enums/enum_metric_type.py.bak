from __future__ import annotations

"""
Metric Type Enum.

Strongly typed metric type values for infrastructure metrics.
"""


from enum import Enum, unique


@unique
class EnumMetricType(str, Enum):
    """Strongly typed metric type values."""

    PERFORMANCE = "performance"
    SYSTEM = "system"
    BUSINESS = "business"
    CUSTOM = "custom"
    HEALTH = "health"


# Export for use
__all__ = ["EnumMetricType"]
