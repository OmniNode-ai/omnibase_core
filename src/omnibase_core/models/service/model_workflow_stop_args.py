from uuid import UUID

from pydantic import Field

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
WorkflowStopArgs model.
"""

from pydantic import BaseModel


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
