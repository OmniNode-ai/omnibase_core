"""
Action Configuration Parameter Model.

Defines strongly-typed parameters for action configuration in FSM transitions.
Each parameter specifies its name, type, whether it's required, and an optional default value.

This model is a key component of the FSM contract system, enabling type-safe
configuration of transition actions in NodeReducer contracts.

Strict typing is enforced: No Any types allowed in public interface.

See Also:
    - docs/specs/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: NodeReducer contract specification
    - ModelFSMTransitionAction: Uses ModelActionConfigParameter for action parameters
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type alias for supported parameter types
ParameterType = Literal[  # enum-ok: model type annotation
    "string", "int", "bool", "float", "list", "dict"
]

# Mapping from type string to Python types for validation
_TYPE_MAPPING: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "int": (int,),
    "bool": (bool,),
    "float": (float, int),  # int is acceptable for float
    "list": (list,),
    "dict": (dict,),
}


class ModelActionConfigParameter(BaseModel):
    """
    Strongly-typed parameter definition for action configuration.

    Defines a single parameter for FSM transition action configuration,
    including its name, type, whether it's required, and an optional default value.
    The default value, when provided, must match the declared type.

    This model enables type-safe configuration of actions in NodeReducer
    FSM contracts, ensuring that action parameters are validated at
    contract parse time rather than at runtime.

    Attributes:
        name: Parameter name (identifier). Must be a non-empty string.
        type: Parameter type. One of: string, int, bool, float, list, dict.
        required: Whether the parameter is required. If True, the parameter
            must be provided when configuring the action.
        default: Default value for the parameter. When provided, must match
            the declared type. Only applicable when required=False.
        description: Human-readable description of the parameter's purpose.

    Example:
        >>> param = ModelActionConfigParameter(
        ...     name="timeout_seconds",
        ...     type="int",
        ...     required=False,
        ...     default=30,
        ...     description="Timeout for the operation in seconds"
        ... )
        >>> param.name
        'timeout_seconds'
        >>> param.type
        'int'
        >>> param.default
        30

    See Also:
        - docs/specs/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: NodeReducer contract specification
        - ModelFSMTransitionAction: Uses this model for action parameters
    """

    name: str = Field(
        ...,
        description="Parameter name (identifier)",
        min_length=1,
    )

    type: ParameterType = Field(
        ...,
        description="Parameter type: string, int, bool, float, list, or dict",
    )

    required: bool = Field(
        ...,
        description="Whether the parameter is required",
    )

    default: Any | None = Field(
        default=None,
        description="Default value for the parameter (must match declared type)",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the parameter",
    )

    @model_validator(mode="after")
    def validate_default_matches_type(self) -> ModelActionConfigParameter:
        """Validate that the default value matches the declared type when provided.

        This validator ensures type safety by checking that when a default value
        is provided, it is compatible with the declared parameter type.

        Raises:
            ModelOnexError: If the default value type does not match the declared type.

        Returns:
            The validated model instance.
        """
        if self.default is None:
            return self

        expected_types = _TYPE_MAPPING.get(self.type)
        if expected_types is None:
            # This shouldn't happen due to Literal validation, but defensive check
            msg = f"Unknown parameter type: {self.type}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("type_error"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                        "parameter_name": ModelSchemaValue.from_value(self.name),
                        "declared_type": ModelSchemaValue.from_value(self.type),
                    }
                ),
            )

        # Special case: bool is a subclass of int in Python, so we need explicit check
        if self.type == "int" and isinstance(self.default, bool):
            msg = (
                f"Default value for parameter '{self.name}' has type 'bool', "
                f"expected type '{self.type}'"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("type_mismatch"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                        "parameter_name": ModelSchemaValue.from_value(self.name),
                        "declared_type": ModelSchemaValue.from_value(self.type),
                        "actual_type": ModelSchemaValue.from_value(
                            type(self.default).__name__
                        ),
                        "default_value": ModelSchemaValue.from_value(str(self.default)),
                    }
                ),
            )

        if not isinstance(self.default, expected_types):
            actual_type = type(self.default).__name__
            msg = (
                f"Default value for parameter '{self.name}' has type '{actual_type}', "
                f"expected type '{self.type}'"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("type_mismatch"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                        "parameter_name": ModelSchemaValue.from_value(self.name),
                        "declared_type": ModelSchemaValue.from_value(self.type),
                        "actual_type": ModelSchemaValue.from_value(actual_type),
                        "default_value": ModelSchemaValue.from_value(str(self.default)),
                    }
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        frozen=True,
        use_enum_values=False,
    )


__all__ = ["ModelActionConfigParameter", "ParameterType"]
