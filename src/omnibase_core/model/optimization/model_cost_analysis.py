"""
Model for cost analysis.

Cost analysis and optimization recommendations.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.optimization.enum_cost_tier import EnumCostTier
from omnibase_core.model.optimization.model_cost_breakdown import ModelCostBreakdown
from omnibase_core.model.optimization.model_cost_projection import ModelCostProjection
from omnibase_core.model.optimization.model_efficiency_metrics import (
    ModelEfficiencyMetrics,
)
from omnibase_core.model.optimization.model_optimization_opportunity import (
    ModelOptimizationOpportunity,
)


class ModelCostAnalysis(BaseModel):
    """Cost analysis and optimization recommendations."""

    analysis_id: str = Field(..., description="Unique analysis ID")
    period_start: datetime = Field(..., description="Analysis period start")
    period_end: datetime = Field(..., description="Analysis period end")

    total_tokens: int = Field(..., ge=0, description="Total tokens consumed")
    total_cost: float = Field(..., ge=0, description="Total cost in USD")

    cost_tier: EnumCostTier = Field(..., description="Current cost tier")

    cost_by_category: ModelCostBreakdown = Field(
        default_factory=ModelCostBreakdown,
        description="Cost breakdown by usage category",
    )

    cost_by_window: ModelCostBreakdown = Field(
        default_factory=ModelCostBreakdown,
        description="Cost breakdown by operational window",
    )

    efficiency_metrics: ModelEfficiencyMetrics = Field(
        default_factory=ModelEfficiencyMetrics,
        description="Efficiency metrics",
    )

    optimization_opportunities: list[ModelOptimizationOpportunity] = Field(
        default_factory=list,
        description="Identified optimization opportunities",
    )

    projections: ModelCostProjection = Field(
        default_factory=lambda: ModelCostProjection(
            daily_projection=0.0,
            weekly_projection=0.0,
            monthly_projection=0.0,
            trend="stable",
            confidence=0.0,
        ),
        description="Cost projections",
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Cost optimization recommendations",
    )

    def calculate_roi(self, value_generated: float) -> float:
        """Calculate return on investment."""
        if self.total_cost == 0:
            return 0.0
        return (value_generated - self.total_cost) / self.total_cost

    def get_cost_per_token(self) -> float:
        """Get average cost per token."""
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost / self.total_tokens

    def get_daily_average_cost(self) -> float:
        """Get daily average cost."""
        days = (self.period_end - self.period_start).days
        if days == 0:
            return self.total_cost
        return self.total_cost / days
