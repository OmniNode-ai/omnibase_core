"""
Workflow dispatch model.
"""

from pydantic import BaseModel, Field

from .model_workflow_input import ModelWorkflowInput


class ModelWorkflowDispatch(BaseModel):
    """
    Workflow dispatch configuration with typed fields.
    Replaces Dict[str, Any] for workflow_dispatch fields.
    """

    inputs: dict[str, ModelWorkflowInput] = Field(
        default_factory=dict,
        description="Workflow input definitions",
    )
