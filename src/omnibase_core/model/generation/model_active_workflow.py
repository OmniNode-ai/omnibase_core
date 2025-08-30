"""
Active Workflow Model for Generation Event Handler

ONEX-compliant model for tracking active workflow states.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.ai_workflows.model_workflow_state import EnumWorkflowStatus


class ModelActiveWorkflow(BaseModel):
    """Active workflow tracking for generation event handler."""

    workflow_id: str = Field(description="Unique workflow identifier")
    event_type: str = Field(description="Type of event being processed")
    correlation_id: str = Field(description="Correlation ID for tracking")
    status: EnumWorkflowStatus = Field(description="Current workflow status")
    contract_path: str | None = Field(
        default=None,
        description="Path to contract file if applicable",
    )
    output_path: str | None = Field(
        default=None,
        description="Output directory path if applicable",
    )
    tool_name: str | None = Field(
        default=None,
        description="Name of tool being generated",
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Workflow start time",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Workflow completion time",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if workflow failed",
    )
    result_data: str | None = Field(
        default=None,
        description="Serialized result data as JSON string",
    )
