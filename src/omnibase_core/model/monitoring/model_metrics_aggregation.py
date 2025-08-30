"""
Model for metrics aggregation.

Aggregated metrics over time periods.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMetricsAggregation(BaseModel):
    """Aggregated metrics over time periods."""

    aggregation_id: str = Field(..., description="Unique aggregation identifier")
    period_start: datetime = Field(..., description="Aggregation period start")
    period_end: datetime = Field(..., description="Aggregation period end")
    interval_minutes: int = Field(
        ..., gt=0, description="Aggregation interval in minutes"
    )

    avg_throughput: float = Field(0.0, ge=0, description="Average throughput")
    avg_success_rate: float = Field(
        0.0, ge=0, le=100, description="Average success rate"
    )
    avg_efficiency: float = Field(0.0, ge=0, le=100, description="Average efficiency")
    avg_cost_per_task: float = Field(0.0, ge=0, description="Average cost per task")

    max_queue_depth: int = Field(0, ge=0, description="Maximum queue depth")
    total_errors: int = Field(0, ge=0, description="Total errors in period")
    total_tasks: int = Field(0, ge=0, description="Total tasks in period")
    total_cost: float = Field(0.0, ge=0, description="Total cost in period")

    uptime_percent: float = Field(
        0.0, ge=0, le=100, description="System uptime percentage"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Aggregation timestamp"
    )
