from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType
from omnibase_core.models.configuration.model_workflow_configuration import (
    ModelWorkflowConfiguration,
)

from .model_workflow_input_parameters import ModelWorkflowInputParameters


class ModelWorkflowDataBase(BaseModel):
    """Base workflow data with discriminator."""

    workflow_type: EnumWorkflowType = Field(
        default=...,
        description="Workflow type discriminator",
    )
    input_parameters: ModelWorkflowInputParameters = Field(
        default_factory=ModelWorkflowInputParameters,
        description="Structured workflow input parameters",
    )
    configuration: ModelWorkflowConfiguration = Field(
        default_factory=ModelWorkflowConfiguration,
        description="Structured workflow configuration settings",
    )
