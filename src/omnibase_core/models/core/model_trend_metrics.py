"""
Trend analysis metrics model.

Strongly typed model for trend analysis metrics with enum support,
validation, and confidence intervals.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from ...enums.enum_trend_direction import EnumTrendDirection
from ...enums.enum_trend_type import EnumTrendType


class ModelTrendMetrics(BaseModel):
    """Strongly typed trend analysis metrics with validation."""

    # Unique identification
    metrics_id: UUID = Field(default_factory=uuid4, description="Unique metrics identifier")

    # Core statistical metrics
    min_value: float = Field(..., description="Minimum value in trend")
    max_value: float = Field(..., description="Maximum value in trend")
    avg_value: float = Field(..., description="Average value")
    median_value: float = Field(..., description="Median value")
    std_deviation: float = Field(default=0.0, ge=0.0, description="Standard deviation")

    # Trend analysis
    trend_direction: EnumTrendDirection = Field(
        ...,
        description="Trend direction using strongly typed enum"
    )
    trend_type: EnumTrendType = Field(
        default=EnumTrendType.LINEAR,
        description="Type of trend pattern"
    )
    change_percent: float = Field(
        default=0.0,
        description="Percentage change from start to end"
    )

    # Quality and confidence metrics
    confidence_level: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Confidence level for metrics (0.0-1.0)"
    )
    r_squared: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="R-squared value for trend fit"
    )

    # Range and volatility
    range_value: float = Field(
        default=0.0,
        ge=0.0,
        description="Range (max - min)"
    )
    volatility: float = Field(
        default=0.0,
        ge=0.0,
        description="Volatility metric"
    )

    # Sample size and time span
    sample_size: int = Field(
        default=0,
        ge=0,
        description="Number of data points used"
    )
    time_span_days: float = Field(
        default=0.0,
        ge=0.0,
        description="Time span in days"
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    @field_validator("min_value", "max_value", "avg_value", "median_value")
    @classmethod
    def validate_values(cls, v: float) -> float:
        """Validate that values are finite numbers."""
        if not isinstance(v, (int, float)):
            raise ValueError("Value must be a number")
        if not (-1e15 <= v <= 1e15):  # Reasonable bounds
            raise ValueError("Value must be within reasonable bounds")
        return float(v)

    @field_validator("confidence_level", "r_squared")
    @classmethod
    def validate_ratios(cls, v: float) -> float:
        """Validate that ratio values are between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Ratio must be between 0.0 and 1.0")
        return v

    @model_validator(mode='after')
    def validate_min_max_relationship(self) -> 'ModelTrendMetrics':
        """Validate that min_value <= max_value and calculate range."""
        if self.min_value > self.max_value:
            raise ValueError("Minimum value cannot be greater than maximum value")

        # Auto-calculate range if not set
        if self.range_value == 0.0:
            object.__setattr__(self, 'range_value', self.max_value - self.min_value)

        return self

    def is_high_confidence(self) -> bool:
        """Check if metrics have high confidence."""
        return self.confidence_level >= 0.9 and self.r_squared >= 0.8

    def is_volatile(self) -> bool:
        """Check if trend is volatile based on volatility metric."""
        return self.volatility > 0.2 or self.trend_direction == EnumTrendDirection.VOLATILE

    def is_significant_trend(self) -> bool:
        """Check if trend is statistically significant."""
        return (
            abs(self.change_percent) > 5.0 and
            self.confidence_level >= 0.8 and
            self.sample_size >= 10
        )

    def get_trend_strength(self) -> float:
        """Calculate trend strength based on multiple factors."""
        strength = 0.0

        # R-squared contribution (0-0.4)
        strength += self.r_squared * 0.4

        # Change percent contribution (0-0.3)
        normalized_change = min(abs(self.change_percent) / 100.0, 1.0)
        strength += normalized_change * 0.3

        # Confidence contribution (0-0.2)
        strength += self.confidence_level * 0.2

        # Sample size contribution (0-0.1)
        normalized_sample = min(self.sample_size / 100.0, 1.0)
        strength += normalized_sample * 0.1

        return min(strength, 1.0)

    def get_direction_confidence(self) -> float:
        """Get confidence in the trend direction."""
        base_confidence = self.confidence_level

        # Adjust based on trend strength
        strength_factor = self.get_trend_strength()

        # Adjust based on volatility (lower confidence for volatile trends)
        volatility_factor = 1.0 - min(self.volatility, 0.5)

        return base_confidence * strength_factor * volatility_factor

    @classmethod
    def calculate_from_values(
        cls,
        values: list[float],
        trend_direction: EnumTrendDirection,
        trend_type: EnumTrendType = EnumTrendType.LINEAR,
        **kwargs: Any
    ) -> "ModelTrendMetrics":
        """Calculate metrics from a list of values."""
        if not values:
            raise ValueError("Cannot calculate metrics from empty values list")

        sorted_values = sorted(values)
        n = len(values)

        # Basic statistics
        min_val = sorted_values[0]
        max_val = sorted_values[-1]
        avg_val = sum(values) / n
        median_val = sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2

        # Standard deviation
        variance = sum((x - avg_val) ** 2 for x in values) / n
        std_dev = variance ** 0.5

        # Change percent
        change_pct = 0.0
        if len(values) >= 2 and values[0] != 0:
            change_pct = ((values[-1] - values[0]) / values[0]) * 100

        # Filter out conflicting kwargs
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in {'min_value', 'max_value', 'avg_value', 'median_value',
                                      'std_deviation', 'trend_direction', 'trend_type',
                                      'change_percent', 'sample_size'}}

        return cls(
            min_value=min_val,
            max_value=max_val,
            avg_value=avg_val,
            median_value=median_val,
            std_deviation=std_dev,
            trend_direction=trend_direction,
            trend_type=trend_type,
            change_percent=change_pct,
            sample_size=n,
            **filtered_kwargs
        )