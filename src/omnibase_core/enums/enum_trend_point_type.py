"""
Trend point type enumeration for trend data classification.

Provides strongly typed trend point type values for trend point analysis.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumTrendPointType(str, Enum):
    """
    Strongly typed trend point type for trend data classification.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    DATA_POINT = "data_point"
    PEAK = "peak"
    TROUGH = "trough"
    INFLECTION = "inflection"
    OUTLIER = "outlier"
    BREAKPOINT = "breakpoint"
    SUPPORT = "support"
    RESISTANCE = "resistance"
    MOVING_AVERAGE = "moving_average"
    TREND_LINE = "trend_line"
    REGRESSION_POINT = "regression_point"
    PREDICTED = "predicted"
    INTERPOLATED = "interpolated"
    EXTRAPOLATED = "extrapolated"
    ANOMALY = "anomaly"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_actual_data(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type is actual data."""
        return point_type in {cls.DATA_POINT, cls.PEAK, cls.TROUGH, cls.INFLECTION, cls.OUTLIER, cls.ANOMALY}

    @classmethod
    def is_derived(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type is derived."""
        return point_type in {cls.MOVING_AVERAGE, cls.TREND_LINE, cls.REGRESSION_POINT}

    @classmethod
    def is_predicted(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type is predicted."""
        return point_type in {cls.PREDICTED, cls.INTERPOLATED, cls.EXTRAPOLATED}

    @classmethod
    def is_technical(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type is technical analysis."""
        return point_type in {cls.SUPPORT, cls.RESISTANCE, cls.BREAKPOINT}

    @classmethod
    def is_significant(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type is significant."""
        return point_type in {cls.PEAK, cls.TROUGH, cls.INFLECTION, cls.BREAKPOINT, cls.OUTLIER, cls.ANOMALY}

    @classmethod
    def requires_calculation(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type requires calculation."""
        return point_type in {cls.MOVING_AVERAGE, cls.TREND_LINE, cls.REGRESSION_POINT, cls.PREDICTED, cls.INTERPOLATED, cls.EXTRAPOLATED}

    @classmethod
    def is_extreme(cls, point_type: "EnumTrendPointType") -> bool:
        """Check if the trend point type represents an extreme value."""
        return point_type in {cls.PEAK, cls.TROUGH, cls.OUTLIER, cls.ANOMALY}


# Export for use
__all__ = ["EnumTrendPointType"]