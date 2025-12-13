"""
Trend analysis metrics model.
"""

from pydantic import BaseModel, Field


class ModelTrendMetrics(BaseModel):
    """Trend analysis metrics."""

    min_value: float = Field(default=..., description="Minimum value in trend")
    max_value: float = Field(default=..., description="Maximum value in trend")
    avg_value: float = Field(default=..., description="Average value")
    median_value: float = Field(default=..., description="Median value")
    std_deviation: float | None = Field(default=None, description="Standard deviation")
    trend_direction: str = Field(
        default=..., description="Trend direction (up/down/stable)"
    )
    change_percent: float | None = Field(default=None, description="Percentage change")
