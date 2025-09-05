"""Workflow result model for Reducer Pattern Engine."""

from pydantic import BaseModel, Field

from .model_workflow_result_data import ModelWorkflowResultData


class ModelWorkflowResult(BaseModel):
    """Result model for workflow processing."""

    success: bool = Field(..., description="Whether the workflow processing succeeded")
    data: ModelWorkflowResultData = Field(
        default_factory=ModelWorkflowResultData,
        description="Strongly typed result data from processing",
    )
    status_code: str = Field("", description="Status code for the result")
    message: str = Field("", description="Human-readable message about the result")
    output_format: str = Field("json", description="Format of the output data")
