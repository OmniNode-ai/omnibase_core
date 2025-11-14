"""
Pydantic models for workflow operation arguments.

Defines the argument models for workflow execution and management operations
within the ONEX architecture.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.operations.model_workflow_parameters import (
    ModelWorkflowParameters,
)

from .model_workflow_stop_args import ModelWorkflowStopArgs


class ModelWorkflowExecutionArgs(BaseModel):
    """
    Arguments for workflow execution operations.

    Contains the parameters needed to execute a workflow.
    """

    workflow_name: str = Field(
        default=..., description="Name of the workflow to execute"
    )
    parameters: ModelWorkflowParameters | None = Field(
        default=None,
        description="Workflow execution parameters",
    )
    dry_run: bool = Field(default=False, description="Whether to perform a dry run")
    timeout_seconds: int | None = Field(
        default=None,
        description="Execution timeout in seconds",
    )
    priority: str | None = Field(default=None, description="Execution priority")
    tags: list[str] | None = Field(
        default=None,
        description="Tags for the workflow execution",
    )


# Re-export for current standards
__all__ = ["ModelWorkflowExecutionArgs", "ModelWorkflowStopArgs"]
