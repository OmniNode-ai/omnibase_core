from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType

from .model_workflow_data_base import ModelWorkflowDataBase


class ModelParallelWorkflowData(ModelWorkflowDataBase):
    """Parallel workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.PARALLEL] = Field(
        default=EnumWorkflowType.PARALLEL,
        description="Parallel workflow type",
    )
    parallel_branches: list[list[str]] = Field(
        default=...,
        description="Parallel execution branches",
    )
    synchronization_points: list[str] = Field(
        default_factory=list,
        description="Points where parallel branches synchronize",
    )
    max_concurrency: int = Field(
        default=4,
        description="Maximum number of parallel executions",
    )
    failure_strategy: str = Field(
        default="fail_fast",
        description="Strategy when parallel branch fails",
    )
