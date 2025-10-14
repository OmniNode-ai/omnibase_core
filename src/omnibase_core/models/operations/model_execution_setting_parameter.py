from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_parameter_type import EnumWorkflowParameterType
from omnibase_core.models.operations.model_base_workflow_parameter import (
    ModelBaseWorkflowParameter,
)


class ModelExecutionSettingParameter(ModelBaseWorkflowParameter):
    """Execution setting parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.EXECUTION_SETTING] = Field(
        default=EnumWorkflowParameterType.EXECUTION_SETTING,
        description="Execution setting parameter type",
    )
    setting_name: str = Field(default=..., description="Setting name")
    enabled: bool = Field(default=True, description="Whether setting is enabled")
    conditional: bool = Field(
        default=False,
        description="Whether setting is conditional",
    )
    dependency: str = Field(default="", description="Dependency for setting")
