"""
Workflow input model.
"""

from pydantic import BaseModel, Field


class ModelWorkflowInput(BaseModel):
    """Individual workflow input definition."""

    description: str = Field(..., description="Input description")
    required: bool = Field(False, description="Whether input is required")
    default: str | int | bool | None = Field(None, description="Default value")
    type: str = Field("string", description="Input type (string/choice/boolean)")
    options: list[str] | None = Field(None, description="Options for choice type")
