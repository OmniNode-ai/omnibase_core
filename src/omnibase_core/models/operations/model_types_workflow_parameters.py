from typing import Annotated

from pydantic import Field

from omnibase_core.models.operations.model_environment_variable_parameter import (
    ModelEnvironmentVariableParameter,
)
from omnibase_core.models.operations.model_execution_setting_parameter import (
    ModelExecutionSettingParameter,
)
from omnibase_core.models.operations.model_resource_limit_parameter import (
    ModelResourceLimitParameter,
)
from omnibase_core.models.operations.model_timeout_setting_parameter import (
    ModelTimeoutSettingParameter,
)
from omnibase_core.models.operations.model_workflow_config_parameter import (
    ModelWorkflowConfigParameter,
)

# ONEX-compatible discriminated unions (max 4 members each)
# Configuration and Execution Parameters Union
ConfigExecutionParameterUnion = Annotated[
    ModelWorkflowConfigParameter
    | ModelExecutionSettingParameter
    | ModelTimeoutSettingParameter
    | ModelEnvironmentVariableParameter,
    Field(discriminator="parameter_type"),
]

# Primary discriminated union for workflow parameters (5 members max - ONEX compliant)
ModelWorkflowParameterValue = Annotated[
    ModelWorkflowConfigParameter
    | ModelExecutionSettingParameter
    | ModelTimeoutSettingParameter
    | ModelEnvironmentVariableParameter
    | ModelResourceLimitParameter,
    Field(discriminator="parameter_type"),
]
