from typing import Any, Union

from pydantic import BaseModel, Field, validator

from omnibase_core.enums.enum_json_value_type import EnumJsonValueType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelJsonField(BaseModel):
    """
    ONEX-compliant strongly typed JSON field with protocol constraints.

    Uses discriminated union pattern for type safety without factory methods.
    """

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

    # ONEX validation constraints
    @validator("string_value")
    def validate_string_type_consistency(self, v: Any, values: dict[str, Any]) -> Any:
        """Ensure string_value is set only when field_type=STRING."""
        field_type = values.get("field_type")
        if field_type == EnumJsonValueType.STRING and v is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="string_value must be provided when field_type=STRING",
            )
        if field_type != EnumJsonValueType.STRING and v is not None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"string_value must be None when field_type={field_type}",
            )
        return v

    @validator("number_value")
    def validate_number_type_consistency(self, v: Any, values: dict[str, Any]) -> Any:
        """Ensure number_value is set only when field_type=NUMBER."""
        field_type = values.get("field_type")
        if field_type == EnumJsonValueType.NUMBER and v is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="number_value must be provided when field_type=NUMBER",
            )
        if field_type != EnumJsonValueType.NUMBER and v is not None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"number_value must be None when field_type={field_type}",
            )
        return v

    @validator("boolean_value")
    def validate_boolean_type_consistency(self, v: Any, values: dict[str, Any]) -> Any:
        """Ensure boolean_value is set only when field_type=BOOLEAN."""
        field_type = values.get("field_type")
        if field_type == EnumJsonValueType.BOOLEAN and v is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="boolean_value must be provided when field_type=BOOLEAN",
            )
        if field_type != EnumJsonValueType.BOOLEAN and v is not None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"boolean_value must be None when field_type={field_type}",
            )
        return v

    @validator("array_values")
    def validate_array_type_consistency(self, v: Any, values: dict[str, Any]) -> Any:
        """Ensure array_values is set only when field_type=ARRAY."""
        field_type = values.get("field_type")
        if field_type == EnumJsonValueType.ARRAY and v is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="array_values must be provided when field_type=ARRAY",
            )
        if field_type != EnumJsonValueType.ARRAY and v is not None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"array_values must be None when field_type={field_type}",
            )
        return v

    def get_typed_value(self) -> Any:
        """ONEX-compliant value accessor with strong typing."""
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
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unknown field_type: {self.field_type}",
                )
