from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_parameter_type import EnumWorkflowParameterType
from omnibase_core.models.operations.model_base_workflow_parameter import (
    ModelBaseWorkflowParameter,
)


class ModelResourceLimitParameter(ModelBaseWorkflowParameter):
    """Resource limit parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.RESOURCE_LIMIT] = Field(
        default=EnumWorkflowParameterType.RESOURCE_LIMIT,
        description="Resource limit parameter type",
    )
    resource_type: str = Field(default=..., description="Resource type")
    limit_value: float = Field(default=..., description="Limit value", ge=0.0)
    unit: str = Field(default=..., description="Unit for limit value")
    enforce_hard_limit: bool = Field(
        default=True,
        description="Whether to enforce hard limit",
    )
