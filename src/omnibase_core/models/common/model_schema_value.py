#!/usr/bin/env python3
"""
Model for representing schema values with proper type safety.

This model replaces Any type usage in schema definitions by providing
a structured representation of possible schema values.
"""

from typing import Any

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
    def from_value(cls, value: Any) -> "ModelSchemaValue":
        """
        Create ModelSchemaValue from a Python value.

        Args:
            value: Python value to convert

        Returns:
            ModelSchemaValue instance
        """
        if value is None:
            return cls(value_type="null", null_value=True)
        if isinstance(value, bool):
            return cls(value_type="boolean", boolean_value=value)
        if isinstance(value, str):
            return cls(value_type="string", string_value=value)
        if isinstance(value, int | float):
            return cls(value_type="number", number_value=value)
        if isinstance(value, list):
            return cls(
                value_type="array",
                array_value=[cls.from_value(item) for item in value],
            )
        if isinstance(value, dict):
            return cls(
                value_type="object",
                object_value={k: cls.from_value(v) for k, v in value.items()},
            )
        # Convert to string representation for unknown types
        return cls(value_type="string", string_value=str(value))

    def to_value(self) -> Any:
        """
        Convert back to Python value.

        Returns:
            Python value
        """
        if self.value_type == "null":
            return None
        if self.value_type == "boolean":
            return self.boolean_value
        if self.value_type == "string":
            return self.string_value
        if self.value_type == "number":
            return self.number_value
        if self.value_type == "array":
            return [item.to_value() for item in (self.array_value or [])]
        if self.value_type == "object":
            return {k: v.to_value() for k, v in (self.object_value or {}).items()}
        return None
