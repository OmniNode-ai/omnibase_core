from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

from .model_conditional_workflow_context import ModelConditionalWorkflowContext
from .model_workflow_data_base import ModelWorkflowDataBase


class ModelConditionalWorkflowData(ModelWorkflowDataBase):
    """Conditional workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.CONDITIONAL] = Field(
        default=EnumWorkflowType.CONDITIONAL,
        description="Conditional workflow type",
    )
    condition_expression: str = Field(
        default=..., description="Boolean condition expression"
    )
    true_branch: list[str] = Field(
        default=...,
        description="Steps to execute when condition is true",
    )
    false_branch: list[str] = Field(
        default_factory=list,
        description="Steps to execute when condition is false",
    )
    condition_context: ModelConditionalWorkflowContext = Field(
        default_factory=ModelConditionalWorkflowContext,
        description="Structured context variables for condition evaluation",
    )
