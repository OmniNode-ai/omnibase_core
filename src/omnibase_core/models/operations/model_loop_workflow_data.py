from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

from .model_loop_workflow_context import ModelLoopWorkflowContext
from .model_workflow_data_base import ModelWorkflowDataBase


class ModelLoopWorkflowData(ModelWorkflowDataBase):
    """Loop workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.LOOP] = Field(
        default=EnumWorkflowType.LOOP,
        description="Loop workflow type",
    )
    loop_body: list[str] = Field(
        default=...,
        description="Steps to execute in each loop iteration",
    )
    loop_condition: str = Field(default=..., description="Loop continuation condition")
    max_iterations: int = Field(
        default=100,
        description="Maximum number of loop iterations",
    )
    iteration_context: ModelLoopWorkflowContext = Field(
        default_factory=ModelLoopWorkflowContext,
        description="Structured context variables updated each iteration",
    )
    break_on_error: bool = Field(
        default=True,
        description="Whether to break loop on error",
    )
