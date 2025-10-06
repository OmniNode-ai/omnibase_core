"""Workflow input state model for protocol workflow orchestrator."""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_workflow import ModelWorkflow
from omnibase_core.models.operations.model_workflow_parameters import (
    ModelWorkflowParameters,
)

from .model_config import ModelConfig


class ModelWorkflowInputState(BaseModel):
    """Input state for workflow orchestrator."""

    action: str = Field(
        ...,
        description="Action to perform (process, orchestrate, execute)",
    )
    scenario_id: str = Field(..., description="ID of the scenario to orchestrate")
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    operation_type: str = Field(
        ...,
        description="Type of operation (model_generation, bootstrap_validation, extraction, generic)",
    )
    parameters: ModelWorkflowParameters = Field(
        default_factory=ModelWorkflowParameters,
        description="Workflow execution parameters",
    )
