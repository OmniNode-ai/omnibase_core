"""
Model for representing schema values with proper type safety.

This model replaces Any type usage in schema definitions by providing
a structured representation of possible schema values.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

To avoid circular imports with error_codes, we use TYPE_CHECKING for type hints
and runtime imports in methods that need to raise errors.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.types.type_json import JsonType


class ModelSchemaValue(BaseModel):
    """
    Type-safe representation of schema values.

    This model can represent all valid JSON Schema value types without
    resorting to Any type usage.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Value types (one of these will be set)
    string_value: str | None = Field(default=None, description="String value")
    number_value: ModelNumericValue | None = Field(
        default=None, description="Numeric value"
    )
    boolean_value: bool | None = Field(default=None, description="Boolean value")
    null_value: bool | None = Field(default=None, description="True if value is null")
    array_value: list["ModelSchemaValue"] | None = Field(
        default=None,
        description="Array of values",
    )
    object_value: dict[str, "ModelSchemaValue"] | None = Field(
        default=None,
        description="Object with key-value pairs",
    )

    # Type indicator
    value_type: str = Field(
        default=...,
        description="Type of the value: string, number, boolean, null, array, object",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
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
        if value is None:
            return cls(
                value_type="null",
                string_value=None,
                number_value=None,
                boolean_value=None,
                null_value=True,
                array_value=None,
                object_value=None,
            )
        if isinstance(value, bool):
            return cls(
                value_type="boolean",
                string_value=None,
                number_value=None,
                boolean_value=value,
                null_value=None,
                array_value=None,
                object_value=None,
            )
        if isinstance(value, str):
            return cls(
                value_type="string",
                string_value=value,
                number_value=None,
                boolean_value=None,
                null_value=None,
                array_value=None,
                object_value=None,
            )
        if isinstance(value, (int, float)):
            return cls(
                value_type="number",
                string_value=None,
                number_value=ModelNumericValue.from_numeric(value),
                boolean_value=None,
                null_value=None,
                array_value=None,
                object_value=None,
            )
        if isinstance(value, list):
            return cls(
                value_type="array",
                string_value=None,
                number_value=None,
                boolean_value=None,
                null_value=None,
                array_value=[cls.from_value(item) for item in value],
                object_value=None,
            )
        if isinstance(value, dict):
            return cls(
                value_type="object",
                string_value=None,
                number_value=None,
                boolean_value=None,
                null_value=None,
                array_value=None,
                object_value={k: cls.from_value(v) for k, v in value.items()},
            )
        # Convert to string representation for unknown types
        return cls(
            value_type="string",
            string_value=str(value),
            number_value=None,
            boolean_value=None,
            null_value=None,
            array_value=None,
            object_value=None,
        )

    def to_value(self) -> JsonType:
        """
        Convert back to Python value.

        Returns:
            JSON-compatible Python value (str, int, float, bool, None, list, or dict).
            The return type is JsonType which properly represents all JSON-serializable values.
        """
        if self.value_type == "null":
            return None
        if self.value_type == "boolean":
            return self.boolean_value
        if self.value_type == "string":
            return self.string_value
        if self.value_type == "number":
            return self.number_value.to_python_value() if self.number_value else None
        if self.value_type == "array":
            return [
                item.to_value()
                for item in (self.array_value if self.array_value is not None else [])
            ]
        if self.value_type == "object":
            return {k: v.to_value() for k, v in (self.object_value or {}).items()}
        return None

    # Protocol method implementations

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Note: This is a pure validation method that does NOT throw exceptions
        to avoid circular dependencies. Use validation layer for exception-based validation.
        """
        # Basic validation - ensure value_type matches actual value
        # This is pure data validation without exception throwing
        if self.value_type == "string" and self.string_value is None:
            return False
        if self.value_type == "number" and self.number_value is None:
            return False
        if self.value_type == "boolean" and self.boolean_value is None:
            return False
        if self.value_type == "array" and self.array_value is None:
            return False
        if self.value_type == "object" and self.object_value is None:
            return False
        return True

    # Factory methods for common schema values

    @classmethod
    def create_string(cls, value: str) -> "ModelSchemaValue":
        """Create a string schema value."""
        return cls(
            value_type="string",
            string_value=value,
            number_value=None,
            boolean_value=None,
            null_value=None,
            array_value=None,
            object_value=None,
        )

    @classmethod
    def create_number(cls, value: int | float) -> "ModelSchemaValue":
        """Create a numeric schema value."""
        return cls(
            value_type="number",
            string_value=None,
            number_value=ModelNumericValue.from_numeric(value),
            boolean_value=None,
            null_value=None,
            array_value=None,
            object_value=None,
        )

    @classmethod
    def create_boolean(cls, value: bool) -> "ModelSchemaValue":
        """Create a boolean schema value."""
        return cls(
            value_type="boolean",
            string_value=None,
            number_value=None,
            boolean_value=value,
            null_value=None,
            array_value=None,
            object_value=None,
        )

    @classmethod
    def create_null(cls) -> "ModelSchemaValue":
        """Create a null schema value."""
        return cls(
            value_type="null",
            string_value=None,
            number_value=None,
            boolean_value=None,
            null_value=True,
            array_value=None,
            object_value=None,
        )

    @classmethod
    def create_array(cls, values: list[object]) -> "ModelSchemaValue":
        """Create an array schema value."""
        return cls(
            value_type="array",
            string_value=None,
            number_value=None,
            boolean_value=None,
            null_value=None,
            array_value=[cls.from_value(item) for item in values],
            object_value=None,
        )

    @classmethod
    def create_object(cls, values: dict[str, object]) -> "ModelSchemaValue":
        """Create an object schema value."""
        return cls(
            value_type="object",
            string_value=None,
            number_value=None,
            boolean_value=None,
            null_value=None,
            array_value=None,
            object_value={k: cls.from_value(v) for k, v in values.items()},
        )

    # Type checking utilities

    def is_string(self) -> bool:
        """Check if this is a string value."""
        return self.value_type == "string"

    def is_number(self) -> bool:
        """Check if this is a numeric value."""
        return self.value_type == "number"

    def is_boolean(self) -> bool:
        """Check if this is a boolean value."""
        return self.value_type == "boolean"

    def is_null(self) -> bool:
        """Check if this is a null value."""
        return self.value_type == "null"

    def is_array(self) -> bool:
        """Check if this is an array value."""
        return self.value_type == "array"

    def is_object(self) -> bool:
        """Check if this is an object value."""
        return self.value_type == "object"

    # Value access with type safety

    def get_string(self) -> str:
        """Get string value, raising error if not a string."""
        if not self.is_string():
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.models.errors.model_onex_error import ModelOnexError

            msg = f"Expected string value, got {self.value_type}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.TYPE_MISMATCH)
        return self.string_value or ""

    def get_number(self) -> ModelNumericValue:
        """Get numeric value, raising error if not a number."""
        if not self.is_number():
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.models.errors.model_onex_error import ModelOnexError

            msg = f"Expected numeric value, got {self.value_type}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.TYPE_MISMATCH)
        return self.number_value or ModelNumericValue.from_float(0.0)

    def get_boolean(self) -> bool:
        """Get boolean value, raising error if not a boolean."""
        if not self.is_boolean():
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.models.errors.model_onex_error import ModelOnexError

            msg = f"Expected boolean value, got {self.value_type}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.TYPE_MISMATCH)
        return self.boolean_value or False

    def get_array(self) -> list["ModelSchemaValue"]:
        """Get array value, raising error if not an array."""
        if not self.is_array():
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.models.errors.model_onex_error import ModelOnexError

            msg = f"Expected array value, got {self.value_type}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.TYPE_MISMATCH)
        return self.array_value if self.array_value is not None else []

    def get_object(self) -> dict[str, "ModelSchemaValue"]:
        """Get object value, raising error if not an object."""
        if not self.is_object():
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.models.errors.model_onex_error import ModelOnexError

            msg = f"Expected object value, got {self.value_type}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.TYPE_MISMATCH)
        return self.object_value or {}


# Fix forward references for Pydantic models
try:
    ModelSchemaValue.model_rebuild()
except (
    Exception
):  # error-ok: model_rebuild may fail during circular import resolution, safe to ignore
    pass
