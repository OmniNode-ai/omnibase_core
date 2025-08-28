"""
Core model for workflow metrics information.

Structured model for workflow execution metrics used by
hybrid execution mixins and monitoring systems.
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase.model.core.model_resource_usage_details import ModelResourceUsageDetails
from omnibase.model.core.model_workflow_metrics_details import (
    ModelWorkflowMetricsDetails,
)


class ModelWorkflowMetrics(BaseModel):
    """
    Structured model for workflow execution metrics.

    Used by hybrid execution mixins and workflow monitoring.
    """

    workflow_id: str = Field(description="Unique workflow identifier")
    status: EnumWorkflowStatus = Field(description="Current workflow status")
    start_time: Optional[str] = Field(None, description="Workflow start timestamp")
    end_time: Optional[str] = Field(None, description="Workflow completion timestamp")
    duration_seconds: Optional[float] = Field(
        None, description="Execution duration in seconds"
    )
    steps_total: Optional[int] = Field(
        None, description="Total number of workflow steps"
    )
    steps_completed: Optional[int] = Field(
        None, description="Number of completed steps"
    )
    steps_failed: Optional[int] = Field(None, description="Number of failed steps")
    error_message: Optional[str] = Field(
        None, description="Error message if workflow failed"
    )
    metrics: ModelWorkflowMetricsDetails = Field(
        default_factory=ModelWorkflowMetricsDetails,
        description="Additional workflow metrics",
    )
    resource_usage: ModelResourceUsageDetails = Field(
        default_factory=ModelResourceUsageDetails, description="Resource usage metrics"
    )
