"""
WorkflowStopArgs model.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelWorkflowStopArgs(BaseModel):
    """
    Arguments for workflow stop operations.

    Contains the parameters needed to stop a running workflow.
    """

    workflow_id: UUID = Field(default=..., description="ID of the workflow to stop")
    force: bool = Field(default=False, description="Whether to force stop the workflow")
    reason: str | None = Field(
        default=None, description="Reason for stopping the workflow"
    )
