"""
Trend type enumeration for trend analysis operations.

Provides strongly typed trend type values for trend classification and analysis.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumTrendType(str, Enum):
    """
    Strongly typed trend type for trend analysis operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    CYCLICAL = "cyclical"
    SEASONAL = "seasonal"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_directional(cls, trend_type: "EnumTrendType") -> bool:
        """Check if the trend type is directional."""
        return trend_type in {cls.INCREASING, cls.DECREASING}

    @classmethod
    def is_mathematical(cls, trend_type: "EnumTrendType") -> bool:
        """Check if the trend type is mathematical."""
        return trend_type in {cls.LINEAR, cls.EXPONENTIAL, cls.LOGARITHMIC}

    @classmethod
    def is_temporal(cls, trend_type: "EnumTrendType") -> bool:
        """Check if the trend type is time-based."""
        return trend_type in {cls.CYCLICAL, cls.SEASONAL}

    @classmethod
    def requires_analysis(cls, trend_type: "EnumTrendType") -> bool:
        """Check if the trend type requires detailed analysis."""
        return trend_type in {cls.VOLATILE, cls.CYCLICAL, cls.SEASONAL}


# Export for use
__all__ = ["EnumTrendType"]