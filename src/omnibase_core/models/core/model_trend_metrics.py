from pydantic import Field

"""
Trend analysis metrics model.
"""

from pydantic import BaseModel, Field


class ModelTrendMetrics(BaseModel):
    """Trend analysis metrics."""

    min_value: float = Field(..., description="Minimum value in trend")
    max_value: float = Field(..., description="Maximum value in trend")
    avg_value: float = Field(..., description="Average value")
    median_value: float = Field(..., description="Median value")
    std_deviation: float | None = Field(default=None, description="Standard deviation")
    trend_direction: str = Field(..., description="Trend direction (up/down/stable)")
    change_percent: float | None = Field(default=None, description="Percentage change")
