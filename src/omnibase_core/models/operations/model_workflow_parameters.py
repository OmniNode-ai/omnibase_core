from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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
from omnibase_core.models.operations.model_types_workflow_parameters import (
    ModelWorkflowParameterValue,
)
from omnibase_core.models.operations.model_workflow_config_parameter import (
    ModelWorkflowConfigParameter,
)


class ModelWorkflowParameters(BaseModel):
    """
    Strongly-typed workflow parameters with discriminated unions.

    Replaces primitive soup pattern with specific parameter type classes.
    Implements Core protocols:
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

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
                raise ModelOnexError(
                    message=f"Invalid parameter type for {param_name}: {type(param_value)}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Create deterministic ID from workflow parameters using SHA256
        param_names = sorted(self.workflow_parameters.keys())
        if param_names:
            key_str = "_".join(param_names)
            key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
            return f"workflow_params_{key_hash}"
        raise ModelOnexError(
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

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
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = [
    "ModelEnvironmentVariableParameter",
    "ModelExecutionSettingParameter",
    "ModelResourceLimitParameter",
    "ModelTimeoutSettingParameter",
    "ModelWorkflowConfigParameter",
    "ModelWorkflowParameterValue",
    "ModelWorkflowParameters",
]
