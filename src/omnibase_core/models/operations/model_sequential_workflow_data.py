from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

from .model_workflow_data_base import ModelWorkflowDataBase


class ModelSequentialWorkflowData(ModelWorkflowDataBase):
    """Sequential workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.SEQUENTIAL] = Field(
        default=EnumWorkflowType.SEQUENTIAL,
        description="Sequential workflow type",
    )
    step_sequence: list[str] = Field(
        default=...,
        description="Ordered sequence of workflow steps",
    )
    continue_on_error: bool = Field(
        default=False,
        description="Whether to continue on step failure",
    )
    checkpoint_interval: int = Field(
        default=1,
        description="Number of steps between checkpoints",
    )
    rollback_strategy: str = Field(
        default="stop",
        description="Rollback strategy on failure",
    )
