"""Workflow result model for Reducer Pattern Engine."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class ModelWorkflowResult(BaseModel):
    """Result model for workflow processing."""

    success: bool = Field(..., description="Whether the workflow processing succeeded")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Result data from processing"
    )
    status_code: str = Field("", description="Status code for the result")
    message: str = Field("", description="Human-readable message about the result")
    output_format: str = Field("json", description="Format of the output data")
