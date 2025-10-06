from uuid import UUID

from pydantic import Field

from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.core.model_workflow import ModelWorkflow

from .model_workflow_outputs import ModelWorkflowOutputs
from .model_workflow_parameters import ModelWorkflowParameters


class ModelWorkflowExecutionResult(ModelBaseResult):
    workflow_id: UUID = Field(..., description="ID of the executed workflow")
    status: str = Field(..., description="Execution status")
    outputs: ModelWorkflowOutputs | None = Field(
        default=None,
        description="Workflow execution outputs",
    )
    parameters: ModelWorkflowParameters | None = Field(
        default=None,
        description="Parameters used for execution",
    )
    dry_run: bool | None = Field(default=None, description="Whether this was a dry run")
