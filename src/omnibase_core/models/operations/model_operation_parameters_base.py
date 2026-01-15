"""
Strongly-typed operation parameters model.

Replaces dict[str, Any] usage in operation parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_operation_parameter_type import EnumOperationParameterType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ModelOperationParameterValue"]


# Discriminated parameter union to replace primitive soup pattern
class ModelOperationParameterValue(BaseModel):
    """
    Discriminated union for operation parameter values.

    Replaces Union[StringParameter, NumericParameter, ...] with ONEX-compatible
    discriminated union pattern.
    """

    parameter_type: EnumOperationParameterType = Field(
        description="Parameter type discriminator",
    )
    name: str = Field(default=..., description="Parameter name")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")

    # Value storage fields (only one should be populated based on parameter_type)
    string_value: str | None = None
    numeric_value: float | None = None
    boolean_value: bool | None = None
    list_value: list[str] | None = None
    nested_value: ModelSchemaValue | None = None

    # Type-specific validation fields
    pattern: str | None = Field(
        default=None, description="Regex pattern for string validation"
    )
    min_length: int | None = Field(default=None, description="Minimum string length")
    max_length: int | None = Field(default=None, description="Maximum string length")
    min_value: float | None = Field(default=None, description="Minimum numeric value")
    max_value: float | None = Field(default=None, description="Maximum numeric value")
    precision: int | None = Field(
        default=None, description="Decimal precision for numeric"
    )
    default_value: bool | None = Field(
        default=None, description="Default boolean value"
    )
    allowed_values: list[str] | None = Field(
        default=None, description="Allowed list[Any]values"
    )
    min_items: int | None = Field(default=None, description="Minimum list[Any]items")
    max_items: int | None = Field(default=None, description="Maximum list[Any]items")
    schema_type: str | None = Field(
        default=None, description="Schema type for nested values"
    )

    @field_validator(
        "string_value",
        "numeric_value",
        "boolean_value",
        "list_value",
        "nested_value",
    )
    @classmethod
    def validate_value_type(cls, v: Any, info: ValidationInfo) -> Any:
        """Ensure value matches declared parameter type."""
        if not hasattr(info, "data") or "parameter_type" not in info.data:
            return v

        parameter_type = info.data["parameter_type"]
        field_name = info.field_name

        # Check that the correct field is populated for the type
        expected_fields = {
            EnumOperationParameterType.STRING: "string_value",
            EnumOperationParameterType.NUMERIC: "numeric_value",
            EnumOperationParameterType.BOOLEAN: "boolean_value",
            EnumOperationParameterType.LIST: "list_value",
            EnumOperationParameterType.NESTED: "nested_value",
        }

        expected_field = expected_fields.get(parameter_type)
        if (
            expected_field == field_name
            and v is None
            and parameter_type != EnumOperationParameterType.NESTED
        ):
            raise ModelOnexError(
                message=f"Value required for parameter type {parameter_type}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if expected_field != field_name and v is not None:
            raise ModelOnexError(
                message=f"Unexpected value in {field_name} for parameter type {parameter_type}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    @classmethod
    def from_string(
        cls,
        name: str,
        value: str,
        **kwargs: Any,
    ) -> ModelOperationParameterValue:
        """Create string parameter."""
        return cls(
            parameter_type=EnumOperationParameterType.STRING,
            name=name,
            string_value=value,
            **kwargs,
        )

    @classmethod
    def from_numeric(
        cls,
        name: str,
        value: float,
        **kwargs: Any,
    ) -> ModelOperationParameterValue:
        """Create numeric parameter."""
        return cls(
            parameter_type=EnumOperationParameterType.NUMERIC,
            name=name,
            numeric_value=value,
            **kwargs,
        )

    @classmethod
    def from_boolean(
        cls,
        name: str,
        value: bool,
        **kwargs: Any,
    ) -> ModelOperationParameterValue:
        """Create boolean parameter."""
        return cls(
            parameter_type=EnumOperationParameterType.BOOLEAN,
            name=name,
            boolean_value=value,
            **kwargs,
        )

    @classmethod
    def from_list(
        cls,
        name: str,
        value: list[str],
        **kwargs: Any,
    ) -> ModelOperationParameterValue:
        """Create list[Any]parameter."""
        return cls(
            parameter_type=EnumOperationParameterType.LIST,
            name=name,
            list_value=value,
            **kwargs,
        )

    @classmethod
    def from_nested(
        cls,
        name: str,
        value: ModelSchemaValue,
        **kwargs: Any,
    ) -> ModelOperationParameterValue:
        """Create nested parameter."""
        return cls(
            parameter_type=EnumOperationParameterType.NESTED,
            name=name,
            nested_value=value,
            **kwargs,
        )

    def get_value(self) -> Any:
        """Get the actual parameter value."""
        if self.parameter_type == EnumOperationParameterType.STRING:
            return self.string_value
        if self.parameter_type == EnumOperationParameterType.NUMERIC:
            return self.numeric_value
        if self.parameter_type == EnumOperationParameterType.BOOLEAN:
            return self.boolean_value
        if self.parameter_type == EnumOperationParameterType.LIST:
            return self.list_value
        if self.parameter_type == EnumOperationParameterType.NESTED:
            return self.nested_value
        # Exhaustive case handling - this should never be reached
        raise ModelOnexError(
            message=f"Unknown parameter type: {self.parameter_type}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
