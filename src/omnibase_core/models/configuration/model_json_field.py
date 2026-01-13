from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_json_value_type import EnumJsonValueType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def _validate_type_consistency[T](
    value: T | None,
    info: ValidationInfo,
    expected_type: EnumJsonValueType,
    field_name: str,
) -> T | None:
    """
    Common validation logic for type consistency between field_type and value fields.

    Args:
        value: The field value being validated
        info: Pydantic validation info containing other field values
        expected_type: The EnumJsonValueType this field corresponds to
        field_name: Name of the field for error messages

    Returns:
        The validated value unchanged

    Raises:
        ModelOnexError: If type consistency check fails
    """
    field_type = info.data.get("field_type")
    if field_type == expected_type and value is None:
        raise ModelOnexError(
            message=f"{field_name} must be provided when field_type="
            f"{expected_type.name}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    if field_type != expected_type and value is not None:
        raise ModelOnexError(
            message=f"{field_name} must be None when field_type={field_type}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return value


class ModelJsonField(BaseModel):
    """
    ONEX-compatible strongly typed JSON field with protocol constraints.

    Uses discriminated union pattern for type safety without factory methods.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    field_type: EnumJsonValueType = Field(
        default=...,
        description="JSON field value type",
    )

    # Union field with strong typing - exactly one will be set based on field_type
    string_value: str | None = Field(
        default=None,
        description="String value when field_type=STRING",
        min_length=0,
        max_length=10000,
    )

    number_value: float | None = Field(
        default=None,
        description="Number value when field_type=NUMBER",
    )

    boolean_value: bool | None = Field(
        default=None,
        description="Boolean value when field_type=BOOLEAN",
    )

    array_values: list[str] | None = Field(
        default=None,
        description="Array values when field_type=ARRAY",
    )

    # ONEX validation constraints - use common helper for type consistency checks
    @field_validator("string_value")
    @classmethod
    def validate_string_type_consistency(
        cls, v: str | None, info: ValidationInfo
    ) -> str | None:
        """Ensure string_value is set only when field_type=STRING."""
        return _validate_type_consistency(
            v, info, EnumJsonValueType.STRING, "string_value"
        )

    @field_validator("number_value")
    @classmethod
    def validate_number_type_consistency(
        cls, v: float | None, info: ValidationInfo
    ) -> float | None:
        """Ensure number_value is set only when field_type=NUMBER."""
        return _validate_type_consistency(
            v, info, EnumJsonValueType.NUMBER, "number_value"
        )

    @field_validator("boolean_value")
    @classmethod
    def validate_boolean_type_consistency(
        cls, v: bool | None, info: ValidationInfo
    ) -> bool | None:
        """Ensure boolean_value is set only when field_type=BOOLEAN."""
        return _validate_type_consistency(
            v, info, EnumJsonValueType.BOOLEAN, "boolean_value"
        )

    @field_validator("array_values")
    @classmethod
    def validate_array_type_consistency(
        cls, v: list[str] | None, info: ValidationInfo
    ) -> list[str] | None:
        """Ensure array_values is set only when field_type=ARRAY."""
        return _validate_type_consistency(
            v, info, EnumJsonValueType.ARRAY, "array_values"
        )

    def get_typed_value(self) -> str | float | bool | list[str] | None:
        """ONEX-compatible value accessor with strong typing."""
        match self.field_type:
            case EnumJsonValueType.STRING:
                return self.string_value
            case EnumJsonValueType.NUMBER:
                return self.number_value
            case EnumJsonValueType.BOOLEAN:
                return self.boolean_value
            case EnumJsonValueType.ARRAY:
                return self.array_values
            case EnumJsonValueType.NULL:
                return None
            case _:
                raise ModelOnexError(
                    message=f"Unknown field_type: {self.field_type}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
