"""
Model for efficiency metrics.

Efficiency metrics for cost analysis.
"""

from pydantic import BaseModel, Field


class ModelEfficiencyMetrics(BaseModel):
    """Efficiency metrics for cost analysis."""

    tokens_per_task: float = Field(0.0, description="Average tokens per task")
    cost_per_task: float = Field(0.0, description="Average cost per task")
    success_rate: float = Field(0.0, description="Task success rate")
    utilization_rate: float = Field(0.0, description="Quota utilization rate")
    efficiency_score: float = Field(0.0, description="Overall efficiency score")
