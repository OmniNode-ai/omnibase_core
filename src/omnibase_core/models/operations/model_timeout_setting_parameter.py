from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_workflow_parameter_type import EnumWorkflowParameterType
from omnibase_core.models.operations.model_base_workflow_parameter import (
    ModelBaseWorkflowParameter,
)


class ModelTimeoutSettingParameter(ModelBaseWorkflowParameter):
    """Timeout setting parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.TIMEOUT_SETTING] = Field(
        default=EnumWorkflowParameterType.TIMEOUT_SETTING,
        description="Timeout setting parameter type",
    )
    timeout_name: str = Field(default=..., description="Timeout name")
    timeout_ms: int = Field(default=..., description="Timeout in milliseconds", gt=0)
    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout",
    )
    escalation_timeout_ms: int = Field(
        default=0,
        description="Escalation timeout in milliseconds",
        ge=0,
    )
