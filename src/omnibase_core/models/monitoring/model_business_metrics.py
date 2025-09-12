"""
Model for business metrics.

Business KPIs and trends for monitoring.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.monitoring.enum_trend_direction import EnumTrendDirection


class ModelBusinessMetrics(BaseModel):
    """Business KPIs and trends."""

    development_velocity: float = Field(
        0.0,
        ge=0,
        description="Development velocity in tickets per day",
    )
    cost_efficiency: float = Field(
        0.0,
        ge=0,
        description="Cost efficiency in dollars per ticket",
    )
    quality_score: float = Field(0.0, ge=0, le=100, description="Quality score 0-100")
    roi_metric: float = Field(0.0, description="Return on investment ratio")

    velocity_trend: EnumTrendDirection = Field(
        ...,
        description="Velocity trend direction",
    )
    cost_trend: EnumTrendDirection = Field(..., description="Cost trend direction")
    quality_trend: EnumTrendDirection = Field(
        ...,
        description="Quality trend direction",
    )
    efficiency_improvement_percent: float = Field(
        0.0,
        description="Efficiency improvement percentage",
    )

    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")

    tickets_completed: int = Field(
        0,
        ge=0,
        description="Total tickets completed in period",
    )
    total_cost: float = Field(0.0, ge=0, description="Total cost in period")

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp",
    )
