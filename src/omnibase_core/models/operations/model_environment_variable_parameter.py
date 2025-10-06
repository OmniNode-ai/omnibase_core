from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_parameter_type import EnumWorkflowParameterType
from omnibase_core.models.operations.model_base_workflow_parameter import (
    ModelBaseWorkflowParameter,
)


class ModelEnvironmentVariableParameter(ModelBaseWorkflowParameter):
    """Environment variable parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.ENVIRONMENT_VARIABLE] = Field(
        default=EnumWorkflowParameterType.ENVIRONMENT_VARIABLE,
        description="Environment variable parameter type",
    )
    variable_name: str = Field(default=..., description="Environment variable name")
    variable_value: str = Field(default=..., description="Environment variable value")
    sensitive: bool = Field(default=False, description="Whether variable is sensitive")
    inherit_from_parent: bool = Field(
        default=True,
        description="Whether to inherit from parent",
    )
