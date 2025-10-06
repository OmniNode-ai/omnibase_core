from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Workflow input model.
"""


class ModelWorkflowInput(BaseModel):
    """Individual workflow input definition."""

    description: str = Field(default=..., description="Input description")
    required: bool = Field(default=False, description="Whether input is required")
    default: Any = Field(default=None, description="Default value")
    type: str = Field(
        default="string", description="Input type (string/choice/boolean)"
    )
    options: list[str] | None = Field(
        default=None, description="Options for choice type"
    )
