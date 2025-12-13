"""
Orchestrator metrics model.
"""

from pydantic import BaseModel, Field


class ModelOrchestratorMetrics(BaseModel):
    """Orchestrator performance metrics."""

    active_workflows: int = Field(
        default=0, ge=0, description="Number of active workflows"
    )
    completed_workflows: int = Field(
        default=0,
        ge=0,
        description="Number of completed workflows",
    )
    failed_workflows: int = Field(
        default=0, ge=0, description="Number of failed workflows"
    )
    avg_execution_time_seconds: float | None = Field(
        default=None,
        description="Average execution time",
    )
    resource_utilization_percent: float | None = Field(
        default=None,
        description="Resource utilization",
    )

    def get_total_workflows(self) -> int:
        """Get total number of workflows."""
        return self.active_workflows + self.completed_workflows + self.failed_workflows

    def get_success_rate(self) -> float:
        """Calculate workflow success rate."""
        total = self.completed_workflows + self.failed_workflows
        if total == 0:
            return 0.0
        return (self.completed_workflows / total) * 100
