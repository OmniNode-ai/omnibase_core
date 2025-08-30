from typing import Optional

from pydantic import Field

from omnibase_core.model.core.model_base_result import ModelBaseResult

from .model_workflow_outputs import ModelWorkflowOutputs
from .model_workflow_parameters import ModelWorkflowParameters


class ModelWorkflowExecutionResult(ModelBaseResult):
    workflow_id: str = Field(..., description="ID of the executed workflow")
    status: str = Field(..., description="Execution status")
    outputs: Optional[ModelWorkflowOutputs] = Field(
        None, description="Workflow execution outputs"
    )
    parameters: Optional[ModelWorkflowParameters] = Field(
        None, description="Parameters used for execution"
    )
    dry_run: Optional[bool] = Field(None, description="Whether this was a dry run")
