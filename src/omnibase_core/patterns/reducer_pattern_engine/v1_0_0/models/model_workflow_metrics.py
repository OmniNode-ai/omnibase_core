"""Workflow metrics model for Reducer Pattern Engine."""

from typing import Any

from pydantic import BaseModel, Field


class ModelWorkflowMetrics(BaseModel):
    """
    Metrics for workflow processing performance.

    Tracks performance metrics for monitoring and optimization
    of the Reducer Pattern Engine.
    """

    total_workflows_processed: int = Field(
        0,
        description="Total number of workflows processed",
    )
    successful_workflows: int = Field(
        0,
        description="Number of successful workflow executions",
    )
    failed_workflows: int = Field(0, description="Number of failed workflow executions")
    average_processing_time_ms: float = Field(
        0.0,
        description="Average processing time in milliseconds",
    )
    average_routing_time_ms: float = Field(
        0.0,
        description="Average routing time in milliseconds",
    )
    active_instances: int = Field(
        0,
        description="Number of currently active workflow instances",
    )
    subreducer_metrics: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-subreducer performance metrics",
    )

    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_workflows_processed == 0:
            return 0.0
        return (self.successful_workflows / self.total_workflows_processed) * 100.0
