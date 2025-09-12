"""Workflow execution state model for tracking overall Workflow execution progress."""

from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.models.execution.model_execution_context import ModelExecutionContext
from omnibase_core.models.workflow.model_workflow_execution_config import (
    ModelWorkflowExecutionConfig,
)
from omnibase_core.models.workflow.model_workflow_node_status import (
    ModelWorkflowNodeStatus,
)


class ModelWorkflowExecutionState(BaseModel):
    """Workflow execution state with comprehensive tracking."""

    nodes: dict[str, ModelWorkflowNodeStatus] = Field(
        default_factory=dict,
        description="Node status tracking",
    )
    completed_nodes: set[str] = Field(
        default_factory=set,
        description="Set of completed node IDs",
    )
    failed_nodes: set[str] = Field(
        default_factory=set,
        description="Set of failed node IDs",
    )
    total_nodes: int = Field(default=0, description="Total number of nodes", ge=0)
    execution_context: ModelExecutionContext = Field(
        ...,
        description="Execution context data",
    )
    workflow_execution_config: ModelWorkflowExecutionConfig = Field(
        ...,
        description="Workflow execution configuration",
    )
    temp_directory: Path | None = Field(
        None,
        description="Temporary directory for atomic operations",
    )
    checksums: dict[str, str] = Field(
        default_factory=dict,
        description="File checksums for verification",
    )
