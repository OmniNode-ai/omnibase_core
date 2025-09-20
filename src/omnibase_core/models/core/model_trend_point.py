"""
Trend data point model for time series data.

Strongly typed model with UUID identification, validation, and quality metrics.
Supports confidence intervals and metadata for robust trend analysis.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer, field_validator

from ...enums.enum_trend_point_type import EnumTrendPointType


class ModelTrendPoint(BaseModel):
    """Individual trend data point with strong typing and validation."""

    # Unique identification
    point_id: UUID = Field(default_factory=uuid4, description="Unique point identifier")

    # Core data
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Data point value")
    point_type: EnumTrendPointType = Field(
        default=EnumTrendPointType.DATA_POINT,
        description="Type classification of the trend point"
    )

    # Quality and confidence metrics
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level (0.0-1.0)"
    )
    quality_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Data quality score (0.0-1.0)"
    )

    # Optional metadata
    label: str | None = Field(None, description="Optional label or category")
    source: str | None = Field(None, description="Data source identifier")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    # Validation flags
    is_anomaly: bool = Field(default=False, description="Whether point is an anomaly")
    is_interpolated: bool = Field(default=False, description="Whether value is interpolated")
    is_forecast: bool = Field(default=False, description="Whether point is forecasted")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Validate that value is a finite number."""
        if not isinstance(v, (int, float)):
            raise ValueError("Value must be a number")
        if not (-1e15 <= v <= 1e15):  # Reasonable bounds
            raise ValueError("Value must be within reasonable bounds")
        return float(v)

    @field_validator("confidence", "quality_score")
    @classmethod
    def validate_scores(cls, v: float) -> float:
        """Validate that scores are between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")
        return v

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()

    @field_serializer("point_id")
    def serialize_uuid(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)

    def is_high_quality(self) -> bool:
        """Check if this is a high quality data point."""
        return self.confidence >= 0.8 and self.quality_score >= 0.8

    def is_reliable(self) -> bool:
        """Check if this data point is reliable for analysis."""
        return (
            not self.is_anomaly and
            self.confidence >= 0.5 and
            self.quality_score >= 0.5
        )

    def get_weighted_value(self) -> float:
        """Get value weighted by confidence and quality."""
        weight = (self.confidence + self.quality_score) / 2
        return self.value * weight

    def is_actual_data(self) -> bool:
        """Check if this point represents actual data."""
        return EnumTrendPointType.is_actual_data(self.point_type)

    def is_derived(self) -> bool:
        """Check if this point is derived from calculations."""
        return EnumTrendPointType.is_derived(self.point_type)

    def is_predicted(self) -> bool:
        """Check if this point is predicted/forecasted."""
        return EnumTrendPointType.is_predicted(self.point_type)

    def is_significant(self) -> bool:
        """Check if this point is statistically significant."""
        return EnumTrendPointType.is_significant(self.point_type)

    def is_extreme(self) -> bool:
        """Check if this point represents an extreme value."""
        return EnumTrendPointType.is_extreme(self.point_type)

    @classmethod
    def create_forecast_point(
        cls,
        timestamp: datetime,
        value: float,
        confidence: float = 0.5,
        **kwargs: Any
    ) -> "ModelTrendPoint":
        """Create a forecast data point."""
        return cls(
            timestamp=timestamp,
            value=value,
            point_type=EnumTrendPointType.PREDICTED,
            confidence=confidence,
            is_forecast=True,
            **kwargs
        )

    @classmethod
    def create_interpolated_point(
        cls,
        timestamp: datetime,
        value: float,
        confidence: float = 0.7,
        **kwargs: Any
    ) -> "ModelTrendPoint":
        """Create an interpolated data point."""
        return cls(
            timestamp=timestamp,
            value=value,
            point_type=EnumTrendPointType.INTERPOLATED,
            confidence=confidence,
            is_interpolated=True,
            **kwargs
        )

    @classmethod
    def create_anomaly_point(
        cls,
        timestamp: datetime,
        value: float,
        confidence: float = 0.9,
        **kwargs: Any
    ) -> "ModelTrendPoint":
        """Create an anomaly data point."""
        return cls(
            timestamp=timestamp,
            value=value,
            point_type=EnumTrendPointType.ANOMALY,
            confidence=confidence,
            is_anomaly=True,
            **kwargs
        )

    @classmethod
    def create_peak_point(
        cls,
        timestamp: datetime,
        value: float,
        confidence: float = 0.8,
        **kwargs: Any
    ) -> "ModelTrendPoint":
        """Create a peak data point."""
        return cls(
            timestamp=timestamp,
            value=value,
            point_type=EnumTrendPointType.PEAK,
            confidence=confidence,
            **kwargs
        )

    @classmethod
    def create_trough_point(
        cls,
        timestamp: datetime,
        value: float,
        confidence: float = 0.8,
        **kwargs: Any
    ) -> "ModelTrendPoint":
        """Create a trough data point."""
        return cls(
            timestamp=timestamp,
            value=value,
            point_type=EnumTrendPointType.TROUGH,
            confidence=confidence,
            **kwargs
        )