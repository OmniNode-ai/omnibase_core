"""
Core model for workflow metrics information.

Structured model for workflow execution metrics used by
hybrid execution mixins and monitoring systems.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.core.model_resource_usage_details import (
    ModelResourceUsageDetails,
)
from omnibase_core.models.core.model_workflow_metrics_details import (
    ModelWorkflowMetricsDetails,
)


class ModelWorkflowMetrics(BaseModel):
    """
    Structured model for workflow execution metrics.

    Used by hybrid execution mixins and workflow monitoring.
    """

    workflow_id: UUID = Field(description="Unique workflow identifier")
    status: EnumWorkflowStatus = Field(description="Current workflow status")
    start_time: str | None = Field(default=None, description="Workflow start timestamp")
    end_time: str | None = Field(
        default=None, description="Workflow completion timestamp"
    )
    duration_seconds: float | None = Field(
        default=None,
        description="Execution duration in seconds",
    )
    steps_total: int | None = Field(
        default=None,
        description="Total number of workflow steps",
    )
    steps_completed: int | None = Field(
        default=None,
        description="Number of completed steps",
    )
    steps_failed: int | None = Field(default=None, description="Number of failed steps")
    error_message: str | None = Field(
        default=None,
        description="Error message if workflow failed",
    )
    metrics: ModelWorkflowMetricsDetails = Field(
        default_factory=lambda: ModelWorkflowMetricsDetails(),
        description="Additional workflow metrics",
    )
    resource_usage: ModelResourceUsageDetails = Field(
        default_factory=lambda: ModelResourceUsageDetails(),
        description="Resource usage metrics",
    )
