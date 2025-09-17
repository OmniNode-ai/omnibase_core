"""
Enum for trend direction.

Defines trend direction indicators for metrics.
"""

from enum import Enum


class EnumTrendDirection(str, Enum):
    """Trend direction indicators."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"
