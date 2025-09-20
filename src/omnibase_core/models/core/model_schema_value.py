"""
Model for representing schema values with proper type safety.

This model replaces Any type usage in schema definitions by providing
a structured representation of possible schema values.
"""

from pydantic import BaseModel, Field


class ModelSchemaValue(BaseModel):
    """
    Type-safe representation of schema values.

    This model can represent all valid JSON Schema value types without
    resorting to Any type usage.
    """

    # Value types (one of these will be set)
    string_value: str | None = Field(None, description="String value")
    number_value: int | float | None = Field(None, description="Numeric value")
    boolean_value: bool | None = Field(None, description="Boolean value")
    null_value: bool | None = Field(None, description="True if value is null")
    array_value: list["ModelSchemaValue"] | None = Field(
        None,
        description="Array of values",
    )
    object_value: dict[str, "ModelSchemaValue"] | None = Field(
        None,
        description="Object with key-value pairs",
    )

    # Type indicator
    value_type: str = Field(
        ...,
        description="Type of the value: string, number, boolean, null, array, object",
    )

    @classmethod
    def from_value(cls, value: object) -> "ModelSchemaValue":
        """
        Create ModelSchemaValue from a Python value.

        Args:
            value: Python value to convert

        Returns:
            ModelSchemaValue instance
        """
        # Helper function to create instance with only the relevant field set
        def _create_with_field(
            value_type: str,
            string_value: str | None = None,
            number_value: int | float | None = None,
            boolean_value: bool | None = None,
            null_value: bool | None = None,
            array_value: list["ModelSchemaValue"] | None = None,
            object_value: dict[str, "ModelSchemaValue"] | None = None,
        ) -> "ModelSchemaValue":
            return cls(
                value_type=value_type,
                string_value=string_value,
                number_value=number_value,
                boolean_value=boolean_value,
                null_value=null_value,
                array_value=array_value,
                object_value=object_value,
            )

        # Type dispatch - much more maintainable than giant if/elif chain
        if value is None:
            return _create_with_field("null", null_value=True)

        if isinstance(value, bool):
            return _create_with_field("boolean", boolean_value=value)

        if isinstance(value, str):
            return _create_with_field("string", string_value=value)

        if isinstance(value, (int, float)):
            return _create_with_field("number", number_value=value)

        if isinstance(value, list):
            return _create_with_field(
                "array",
                array_value=[cls.from_value(item) for item in value]
            )

        if isinstance(value, dict):
            return _create_with_field(
                "object",
                object_value={k: cls.from_value(v) for k, v in value.items()}
            )

        # Convert to string representation for unknown types
        return _create_with_field("string", string_value=str(value))

    def to_value(self) -> object:
        """
        Convert back to Python value.

        Returns:
            Python value
        """
        # Type dispatch using dictionary - more maintainable and extensible
        type_handlers = {
            "null": lambda: None,
            "boolean": lambda: self.boolean_value,
            "string": lambda: self.string_value,
            "number": lambda: self.number_value,
            "array": lambda: [item.to_value() for item in (self.array_value or [])],
            "object": lambda: {k: v.to_value() for k, v in (self.object_value or {}).items()}
        }

        handler = type_handlers.get(self.value_type)
        return handler() if handler else None