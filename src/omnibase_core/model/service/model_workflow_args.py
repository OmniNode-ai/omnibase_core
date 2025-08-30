"""
Pydantic models for workflow operation arguments.

Defines the argument models for workflow execution and management operations
within the ONEX architecture.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from .model_workflow_parameters import ModelWorkflowParameters
from .model_workflow_stop_args import ModelWorkflowStopArgs


class ModelWorkflowExecutionArgs(BaseModel):
    """
    Arguments for workflow execution operations.

    Contains the parameters needed to execute a workflow.
    """

    workflow_name: str = Field(..., description="Name of the workflow to execute")
    parameters: Optional[ModelWorkflowParameters] = Field(
        None, description="Workflow execution parameters"
    )
    dry_run: bool = Field(default=False, description="Whether to perform a dry run")
    timeout_seconds: Optional[int] = Field(
        None, description="Execution timeout in seconds"
    )
    priority: Optional[str] = Field(None, description="Execution priority")
    tags: Optional[List[str]] = Field(
        None, description="Tags for the workflow execution"
    )


# Re-export for backward compatibility
__all__ = ["ModelWorkflowExecutionArgs", "ModelWorkflowStopArgs"]
