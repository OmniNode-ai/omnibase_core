"""
Model for trend analysis results in the metrics collector service.

This model defines the structure for trend analysis of metrics.
"""

from pydantic import BaseModel


class ModelTrendAnalysis(BaseModel):
    """Result of trend analysis for a metric."""

    trend_direction: str  # "stable", "increasing", "decreasing"
    slope: float
    correlation: float
    data_points: int
    time_span: str
    current_value: float
    start_value: float
    change_percent: float
