"""Workflow input state model for protocol workflow orchestrator."""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_workflow import ModelWorkflow
from omnibase_core.models.operations.model_workflow_parameters import (
    ModelWorkflowParameters,
)


class ModelWorkflowInputState(BaseModel):
    """Input state for workflow orchestrator."""

    action: str = Field(
        ...,
        description="Action to perform (process, orchestrate, execute)",
    )
    scenario_id: UUID = Field(..., description="ID of the scenario to orchestrate")
    correlation_id: UUID = Field(..., description="Correlation ID for tracking")
    operation_type: str = Field(
        ...,
        description="Type of operation (model_generation, bootstrap_validation, extraction, generic)",
    )
    parameters: ModelWorkflowParameters = Field(
        default_factory=ModelWorkflowParameters,
        description="Workflow execution parameters",
    )
