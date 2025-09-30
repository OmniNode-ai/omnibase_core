"""
Strongly-typed workflow parameters model.

Replaces dict[str, Any] usage in workflow parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_workflow_parameter_type import EnumWorkflowParameterType

# Discriminator function for workflow parameters
# Using Field(discriminator="parameter_type") for discriminated unions


# Base parameter class with common fields
class ModelBaseWorkflowParameter(BaseModel):
    """Base class for all workflow parameters."""

    name: str = Field(..., description="Parameter name")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")


# Specific parameter type classes - eliminates complex optional unions
class ModelWorkflowConfigParameter(ModelBaseWorkflowParameter):
    """Workflow configuration parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.WORKFLOW_CONFIG] = Field(
        default=EnumWorkflowParameterType.WORKFLOW_CONFIG,
        description="Workflow config parameter type",
    )
    config_key: str = Field(..., description="Configuration key")
    config_value: str = Field(..., description="Configuration value")
    config_scope: str = Field(default="workflow", description="Configuration scope")
    overridable: bool = Field(
        default=True,
        description="Whether config can be overridden",
    )


class ModelExecutionSettingParameter(ModelBaseWorkflowParameter):
    """Execution setting parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.EXECUTION_SETTING] = Field(
        default=EnumWorkflowParameterType.EXECUTION_SETTING,
        description="Execution setting parameter type",
    )
    setting_name: str = Field(..., description="Setting name")
    enabled: bool = Field(default=True, description="Whether setting is enabled")
    conditional: bool = Field(
        default=False,
        description="Whether setting is conditional",
    )
    dependency: str = Field(default="", description="Dependency for setting")


class ModelTimeoutSettingParameter(ModelBaseWorkflowParameter):
    """Timeout setting parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.TIMEOUT_SETTING] = Field(
        default=EnumWorkflowParameterType.TIMEOUT_SETTING,
        description="Timeout setting parameter type",
    )
    timeout_name: str = Field(..., description="Timeout name")
    timeout_ms: int = Field(..., description="Timeout in milliseconds", gt=0)
    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout",
    )
    escalation_timeout_ms: int = Field(
        default=0,
        description="Escalation timeout in milliseconds",
        ge=0,
    )


class ModelResourceLimitParameter(ModelBaseWorkflowParameter):
    """Resource limit parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.RESOURCE_LIMIT] = Field(
        default=EnumWorkflowParameterType.RESOURCE_LIMIT,
        description="Resource limit parameter type",
    )
    resource_type: str = Field(..., description="Resource type")
    limit_value: float = Field(..., description="Limit value", ge=0.0)
    unit: str = Field(..., description="Unit for limit value")
    enforce_hard_limit: bool = Field(
        default=True,
        description="Whether to enforce hard limit",
    )


class ModelEnvironmentVariableParameter(ModelBaseWorkflowParameter):
    """Environment variable parameter with specific typing."""

    parameter_type: Literal[EnumWorkflowParameterType.ENVIRONMENT_VARIABLE] = Field(
        default=EnumWorkflowParameterType.ENVIRONMENT_VARIABLE,
        description="Environment variable parameter type",
    )
    variable_name: str = Field(..., description="Environment variable name")
    variable_value: str = Field(..., description="Environment variable value")
    sensitive: bool = Field(default=False, description="Whether variable is sensitive")
    inherit_from_parent: bool = Field(
        default=True,
        description="Whether to inherit from parent",
    )


# ONEX-compliant discriminated unions (max 4 members each)
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


class ModelWorkflowParameters(BaseModel):
    """
    Strongly-typed workflow parameters with discriminated unions.

    Replaces primitive soup pattern with specific parameter type classes.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Use specific parameter types instead of complex optional unions
    workflow_parameters: dict[str, ModelWorkflowParameterValue] = Field(
        default_factory=dict,
        description="Workflow parameters with specific discriminated types",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    @model_validator(mode="after")
    def validate_parameter_types(self) -> ModelWorkflowParameters:
        """Validate that all parameters have correct types."""
        for param_name, param_value in self.workflow_parameters.items():
            if not isinstance(
                param_value,
                (
                    ModelWorkflowConfigParameter,
                    ModelExecutionSettingParameter,
                    ModelTimeoutSettingParameter,
                    ModelEnvironmentVariableParameter,
                    ModelResourceLimitParameter,
                ),
            ):
                raise ValueError(
                    f"Invalid parameter type for {param_name}: {type(param_value)}",
                )
        return self

    # Helper methods for creating specific parameter types
    def add_workflow_config(
        self,
        name: str,
        config_key: str,
        config_value: str,
        config_scope: str = "workflow",
        overridable: bool = True,
        description: str = "",
        required: bool = False,
    ) -> None:
        """Add workflow configuration parameter."""
        self.workflow_parameters[name] = ModelWorkflowConfigParameter(
            name=name,
            config_key=config_key,
            config_value=config_value,
            config_scope=config_scope,
            overridable=overridable,
            description=description,
            required=required,
        )

    def add_execution_setting(
        self,
        name: str,
        setting_name: str,
        enabled: bool = True,
        conditional: bool = False,
        dependency: str = "",
        description: str = "",
        required: bool = False,
    ) -> None:
        """Add execution setting parameter."""
        self.workflow_parameters[name] = ModelExecutionSettingParameter(
            name=name,
            setting_name=setting_name,
            enabled=enabled,
            conditional=conditional,
            dependency=dependency,
            description=description,
            required=required,
        )

    def add_timeout_setting(
        self,
        name: str,
        timeout_name: str,
        timeout_ms: int,
        retry_on_timeout: bool = True,
        escalation_timeout_ms: int = 0,
        description: str = "",
        required: bool = False,
    ) -> None:
        """Add timeout setting parameter."""
        self.workflow_parameters[name] = ModelTimeoutSettingParameter(
            name=name,
            timeout_name=timeout_name,
            timeout_ms=timeout_ms,
            retry_on_timeout=retry_on_timeout,
            escalation_timeout_ms=escalation_timeout_ms,
            description=description,
            required=required,
        )

    def add_resource_limit(
        self,
        name: str,
        resource_type: str,
        limit_value: float,
        unit: str,
        enforce_hard_limit: bool = True,
        description: str = "",
        required: bool = False,
    ) -> None:
        """Add resource limit parameter."""
        self.workflow_parameters[name] = ModelResourceLimitParameter(
            name=name,
            resource_type=resource_type,
            limit_value=limit_value,
            unit=unit,
            enforce_hard_limit=enforce_hard_limit,
            description=description,
            required=required,
        )

    def add_environment_variable(
        self,
        name: str,
        variable_name: str,
        variable_value: str,
        sensitive: bool = False,
        inherit_from_parent: bool = True,
        description: str = "",
        required: bool = False,
    ) -> None:
        """Add environment variable parameter."""
        self.workflow_parameters[name] = ModelEnvironmentVariableParameter(
            name=name,
            variable_name=variable_name,
            variable_value=variable_value,
            sensitive=sensitive,
            inherit_from_parent=inherit_from_parent,
            description=description,
            required=required,
        )

    # Protocol method implementations without Any types

    def execute(self, updates: dict[str, object] | None = None) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            if updates:
                # Update only valid fields with runtime validation
                for key, value in updates.items():
                    if hasattr(self, key) and isinstance(
                        value,
                        (str, bool, int, float),
                    ):
                        setattr(self, key, value)
            return True
        except Exception:
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Create deterministic ID from workflow parameters
        param_names = sorted(self.workflow_parameters.keys())
        if param_names:
            return f"workflow_params_{hash('_'.join(param_names))}"
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(
        self,
    ) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Validate all required parameters are present
            for param in self.workflow_parameters.values():
                if param.required and not param.name:
                    return False
            return True
        except Exception:
            return False


# Export for use
__all__ = [
    "ConfigExecutionParameterUnion",
    "ModelBaseWorkflowParameter",
    "ModelEnvironmentVariableParameter",
    "ModelExecutionSettingParameter",
    "ModelResourceLimitParameter",
    "ModelTimeoutSettingParameter",
    "ModelWorkflowConfigParameter",
    "ModelWorkflowParameterValue",
    "ModelWorkflowParameters",
]
