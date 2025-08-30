"""
Workflow dispatch model.
"""

from typing import Dict

from pydantic import BaseModel, Field

from .model_workflow_input import ModelWorkflowInput


class ModelWorkflowDispatch(BaseModel):
    """
    Workflow dispatch configuration with typed fields.
    Replaces Dict[str, Any] for workflow_dispatch fields.
    """

    inputs: Dict[str, ModelWorkflowInput] = Field(
        default_factory=dict, description="Workflow input definitions"
    )
