"""
Trend analysis metrics model.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelTrendMetrics(BaseModel):
    """Trend analysis metrics."""

    min_value: float = Field(..., description="Minimum value in trend")
    max_value: float = Field(..., description="Maximum value in trend")
    avg_value: float = Field(..., description="Average value")
    median_value: float = Field(..., description="Median value")
    std_deviation: Optional[float] = Field(None, description="Standard deviation")
    trend_direction: str = Field(..., description="Trend direction (up/down/stable)")
    change_percent: Optional[float] = Field(None, description="Percentage change")
