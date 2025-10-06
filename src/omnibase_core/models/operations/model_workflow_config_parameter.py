from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_parameter_type import EnumWorkflowParameterType
from omnibase_core.models.operations.model_base_workflow_parameter import (
    ModelBaseWorkflowParameter,
)


class ModelWorkflowConfigParameter(ModelBaseWorkflowParameter):
    """Workflow configuration parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.WORKFLOW_CONFIG] = Field(
        default=EnumWorkflowParameterType.WORKFLOW_CONFIG,
        description="Workflow config parameter type",
    )
    config_key: str = Field(default=..., description="Configuration key")
    config_value: str = Field(default=..., description="Configuration value")
    config_scope: str = Field(default="workflow", description="Configuration scope")
    overridable: bool = Field(
        default=True,
        description="Whether config can be overridden",
    )
