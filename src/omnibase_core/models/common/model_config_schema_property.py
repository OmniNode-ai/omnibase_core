"""
Typed schema property model for mixin configuration.

This module provides strongly-typed schema properties for configuration patterns,
with full validation of type-default and type-enum consistency.

Supports type aliases:
- 'str' -> 'string'
- 'int' -> 'integer'
- 'bool' -> 'boolean'
- 'float' -> 'number'
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelConfigSchemaProperty(BaseModel):
    """
    Typed schema property for mixin configuration.

    Replaces nested dict[str, Any] in config_schema field
    with explicit typed fields for JSON Schema properties.

    Supports type aliases for common Python type names:
    - 'str' is equivalent to 'string'
    - 'int' is equivalent to 'integer'
    - 'bool' is equivalent to 'boolean'
    - 'float' is equivalent to 'number'

    Supports both ONEX naming (min_value/max_value) and JSON Schema naming
    (minimum/maximum) for numeric constraints. JSON Schema names are
    automatically mapped to ONEX names during validation.
    """

    # Use extra="ignore" to allow JSON Schema fields we don't explicitly model
    # (like 'items' for arrays) without causing validation errors
    model_config = ConfigDict(extra="ignore")

    type: str = Field(
        default="string",
        description="Property type (string, number, integer, boolean, array, object)",
    )
    description: str | None = Field(
        default=None,
        description="Property description",
    )
    default: str | int | float | bool | list[str] | list[int] | None = Field(
        default=None,
        description="Default value (type should match the 'type' field)",
    )
    enum: list[str | int | float | bool | None] | None = Field(
        default=None,
        description="Allowed enum values (supports strings, numbers, booleans, and null)",
    )
    required: bool = Field(
        default=False,
        description="Whether this property is required",
    )
    min_value: float | None = Field(
        default=None,
        description="Minimum value for numeric types",
    )
    max_value: float | None = Field(
        default=None,
        description="Maximum value for numeric types",
    )

    @model_validator(mode="before")
    @classmethod
    def map_json_schema_fields(
        cls, values: dict[str, object] | object
    ) -> dict[str, object] | object:
        """Map JSON Schema field names to ONEX field names.

        JSON Schema uses 'minimum'/'maximum' for numeric constraints,
        while ONEX uses 'min_value'/'max_value'. This validator maps
        the JSON Schema field names to their ONEX equivalents.
        """
        if not isinstance(values, dict):
            return values

        # Map JSON Schema 'minimum' to ONEX 'min_value'
        if "minimum" in values and "min_value" not in values:
            values["min_value"] = values.pop("minimum")
        elif "minimum" in values:
            # Both present, remove 'minimum' as 'min_value' takes precedence
            values.pop("minimum")

        # Map JSON Schema 'maximum' to ONEX 'max_value'
        if "maximum" in values and "max_value" not in values:
            values["max_value"] = values.pop("maximum")
        elif "maximum" in values:
            # Both present, remove 'maximum' as 'max_value' takes precedence
            values.pop("maximum")

        return values

    @model_validator(mode="after")
    def validate_type_default_consistency(self) -> Self:
        """Validate that default value type matches declared type.

        Enforces type consistency between the 'type' field and 'default' value:
        - type="string" requires default to be str
        - type="number" or type="float" requires default to be int or float
        - type="integer" or type="int" requires default to be int (not float)
        - type="boolean" or type="bool" requires default to be bool
        - type="array" accepts list defaults (no element validation)

        Note: int is acceptable for float/number types (widening conversion),
        but bool is NOT acceptable for int types (even though bool is int subclass).

        Raises:
            ModelOnexError: If default value type doesn't match declared type.
        """
        if self.default is not None:
            # Handle list defaults - only valid for array type
            if isinstance(self.default, list):
                if self.type.lower() != "array":
                    raise ModelOnexError(
                        message=(
                            f"Type mismatch: default value has type 'list' "
                            f"but declared type is '{self.type}'. "
                            f"List defaults are only valid for array type."
                        ),
                        error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                        context={
                            "declared_type": self.type,
                            "actual_type": "list",
                            "default_value": str(self.default),
                        },
                    )
            else:
                self._validate_value_type(self.default, "default")

        return self

    @model_validator(mode="after")
    def validate_type_enum_consistency(self) -> Self:
        """Validate that all enum values match the declared type.

        Enforces type consistency between the 'type' field and 'enum' values:
        - type="string" requires all enum values to be str or None
        - type="number" or type="float" requires all enum values to be int, float, or None
        - type="integer" or type="int" requires all enum values to be int or None
        - type="boolean" or type="bool" requires all enum values to be bool or None

        Note: int is acceptable for float/number types (widening conversion),
        but bool is NOT acceptable for int types (even though bool is int subclass).

        Raises:
            ModelOnexError: If any enum value type doesn't match declared type.
        """
        if self.enum is None:
            return self

        for i, enum_value in enumerate(self.enum):
            if enum_value is not None:
                self._validate_value_type(enum_value, f"enum[{i}]", enum_index=i)

        return self

    def _validate_value_type(
        self,
        value: str | int | float | bool,
        field_name: str,
        enum_index: int | None = None,
    ) -> None:
        """Validate a single value against the declared type.

        Args:
            value: The value to validate.
            field_name: Name of the field for error messages (e.g., 'default', 'enum[0]').
            enum_index: Optional index if validating an enum value.

        Raises:
            ModelOnexError: If value type doesn't match declared type.
        """
        declared_type = self.type.lower()
        actual_type = type(value)
        actual_type_name = actual_type.__name__

        # Define type mappings: declared_type -> (valid_types, description)
        type_validations: dict[str, tuple[tuple[type, ...], str]] = {
            "string": ((str,), "string"),
            "str": ((str,), "string"),
            "number": ((int, float), "number (int or float)"),
            "float": ((int, float), "number (int or float)"),
            "integer": ((int,), "integer"),
            "int": ((int,), "integer"),
            "boolean": ((bool,), "boolean"),
            "bool": ((bool,), "boolean"),
        }

        if declared_type not in type_validations:
            # Unknown type, skip validation
            return

        valid_types, type_desc = type_validations[declared_type]

        # Special case: bool is subclass of int, but we don't want bool for int/integer
        if declared_type in ("integer", "int") and isinstance(value, bool):
            context: dict[str, str | int] = {
                "declared_type": self.type,
                "actual_type": actual_type_name,
                f"{field_name}_value": str(value),
            }
            if enum_index is not None:
                context["enum_index"] = enum_index

            raise ModelOnexError(
                message=(
                    f"Type mismatch: {field_name} value has type '{actual_type_name}' "
                    f"but declared type is '{self.type}'. "
                    f"Boolean values are not valid for integer type."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                context=context,
            )

        # For number/float types, also reject bool (bool is int subclass)
        if declared_type in ("number", "float") and isinstance(value, bool):
            context = {
                "declared_type": self.type,
                "actual_type": actual_type_name,
                f"{field_name}_value": str(value),
            }
            if enum_index is not None:
                context["enum_index"] = enum_index

            raise ModelOnexError(
                message=(
                    f"Type mismatch: {field_name} value has type '{actual_type_name}' "
                    f"but declared type is '{self.type}'. "
                    f"Boolean values are not valid for numeric types."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                context=context,
            )

        if not isinstance(value, valid_types):
            context = {
                "declared_type": self.type,
                "actual_type": actual_type_name,
                f"{field_name}_value": str(value),
            }
            if enum_index is not None:
                context["enum_index"] = enum_index

            raise ModelOnexError(
                message=(
                    f"Type mismatch: {field_name} value has type '{actual_type_name}' "
                    f"but declared type is '{self.type}'. "
                    f"Expected {type_desc}."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                context=context,
            )


__all__ = ["ModelConfigSchemaProperty"]
