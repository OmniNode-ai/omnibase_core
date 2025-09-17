"""
WorkflowStopArgs model.
"""

from pydantic import BaseModel, Field


class ModelWorkflowStopArgs(BaseModel):
    """
    Arguments for workflow stop operations.

    Contains the parameters needed to stop a running workflow.
    """

    workflow_id: str = Field(..., description="ID of the workflow to stop")
    force: bool = Field(default=False, description="Whether to force stop the workflow")
    reason: str | None = Field(None, description="Reason for stopping the workflow")
