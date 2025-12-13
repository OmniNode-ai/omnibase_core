"""
Typed schema property model for mixin configuration.

This module provides strongly-typed schema properties for configuration patterns.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Valid JSON Schema types
JsonSchemaType = Literal[
    "string", "integer", "boolean", "number", "array", "object", "null"
]

# Valid enum value types (matches JSON Schema primitive types)
EnumValue = str | int | float | bool | None


class ModelConfigSchemaProperty(BaseModel):
    """
    Typed schema property for mixin configuration.

    Replaces nested dict[str, Any] in config_schema field
    with explicit typed fields for JSON Schema properties.
    """

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
    )

    type: JsonSchemaType = Field(
        default="string",
        description="Property type (string, integer, boolean, number, array, object, null)",
    )
    description: str | None = Field(
        default=None,
        description="Property description",
    )
    default: str | int | float | bool | None = Field(
        default=None,
        description="Default value (type should match the 'type' field)",
    )
    enum: list[EnumValue] | None = Field(
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

    @model_validator(mode="after")
    def _validate_default_type_matches(self) -> "ModelConfigSchemaProperty":
        """Validate that the default value type matches the declared type field."""
        if self.default is None:
            return self

        # Map JSON Schema types to Python types for validation
        type_to_python: dict[str, type | tuple[type, ...]] = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            # Note: "null" type with non-None default is already handled above
        }

        expected_types = type_to_python.get(self.type)
        if expected_types is None:
            # For "null" type, default should be None (already checked above)
            if self.type == "null":
                raise ValueError(
                    f"Default value {self.default!r} is not valid for type 'null'. "
                    "Null type can only have None as default."
                )
            return self

        # Special handling: integer type should not accept float (unless it's a whole number)
        if self.type == "integer" and isinstance(self.default, float):
            if not self.default.is_integer():
                raise ValueError(
                    f"Default value {self.default!r} is a float but type is 'integer'. "
                    "Use an integer value instead."
                )
        elif not isinstance(self.default, expected_types):
            raise ValueError(
                f"Default value {self.default!r} (type: {type(self.default).__name__}) "
                f"does not match declared type '{self.type}'"
            )

        return self


__all__ = ["ModelConfigSchemaProperty", "EnumValue", "JsonSchemaType"]
