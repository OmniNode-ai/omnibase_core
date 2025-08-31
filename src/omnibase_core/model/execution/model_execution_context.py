"""Execution context model for Workflow execution state tracking."""

import time
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.model.execution.model_execution_metadata import (
    ModelExecutionMetadata,
)
from omnibase_core.model.execution.model_execution_result import ModelExecutionResult


class ModelExecutionContext(BaseModel):
    """Model for execution context replacing Dict[str, Any]."""

    correlation_id: str = Field(
        ...,
        description="Correlation ID for tracking",
        min_length=1,
    )
    node_results: dict[str, ModelExecutionResult] = Field(
        default_factory=dict,
        description="Results by node ID",
    )
    workflow_parameters: Any | None = Field(
        None,
        description="Workflow parameters (forward reference)",
    )
    execution_metadata: ModelExecutionMetadata = Field(
        default_factory=lambda: ModelExecutionMetadata(
            start_timestamp=time.time(),
            user_id=None,
            environment=None,
            git_commit=None,
        ),
        description="Execution metadata",
    )
    start_time: float = Field(..., description="Execution start timestamp", gt=0)
    total_nodes: int = Field(default=0, description="Total number of nodes", ge=0)
