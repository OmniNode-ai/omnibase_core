"""
Model for cost projection.

Cost projections for planning.
"""

from pydantic import BaseModel, Field


class ModelCostProjection(BaseModel):
    """Cost projections for planning."""

    daily_projection: float = Field(..., description="Projected daily cost")
    weekly_projection: float = Field(..., description="Projected weekly cost")
    monthly_projection: float = Field(..., description="Projected monthly cost")
    trend: str = Field(..., description="Cost trend direction")
    confidence: float = Field(..., description="Projection confidence")
