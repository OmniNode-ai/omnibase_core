"""
Flexible Value Model - Discriminated Union for Mixed Type Values.

Replaces dict | None, list | None, and other mixed-type unions
with structured discriminated union pattern for type safety.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...exceptions.onex_error import OnexError
from .model_error_context import ModelErrorContext
from .model_schema_value import ModelSchemaValue

# Note: Previously had type aliases (FlexibleDictType, FlexibleListType, FlexibleValueType)
# These were removed to comply with ONEX strong typing standards.
# Using explicit types: dict[str, Any], list[Any], Any




class ModelFlexibleValue(BaseModel):
    """
    Discriminated union for values that can be multiple types.

    Replaces lazy Union[str, dict, list, int, etc.] patterns with
    structured type safety and proper validation.
    """

    value_type: Literal[
        "string",
        "integer",
        "float",
        "boolean",
        "dict",
        "list",
        "uuid",
        "none",
    ] = Field(description="Type discriminator for value")

    # Value storage (only one should be populated)
    string_value: str | None = None
    integer_value: int | None = None
    float_value: float | None = None
    boolean_value: bool | None = None
    dict_value: dict[str, Any] | None = None
    list_value: list[Any] | None = None
    uuid_value: UUID | None = None

    # Metadata
    source: str | None = Field(None, description="Source of the value")
    is_validated: bool = Field(
        default=False, description="Whether value has been validated"
    )

    @model_validator(mode="after")
    def validate_single_value(self) -> ModelFlexibleValue:
        """Ensure only one value is set based on type discriminator."""
        values_map = {
            "string": self.string_value,
            "integer": self.integer_value,
            "float": self.float_value,
            "boolean": self.boolean_value,
            "dict": self.dict_value,
            "list": self.list_value,
            "uuid": self.uuid_value,
            "none": None,
        }

        # Count non-None values
        non_none_count = sum(1 for v in values_map.values() if v is not None)

        # For "none" type, all values should be None
        if self.value_type == "none":
            if non_none_count > 0:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="No values should be set when value_type is 'none'",
                    details=ModelErrorContext.with_context(
                        {
                            "value_type": ModelSchemaValue.from_value(self.value_type),
                            "non_none_count": ModelSchemaValue.from_value(
                                str(non_none_count)
                            ),
                        }
                    ),
                )
        else:
            # For other types, exactly one value should be set
            if non_none_count != 1:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Exactly one value must be set for value_type '{self.value_type}'",
                    details=ModelErrorContext.with_context(
                        {
                            "value_type": ModelSchemaValue.from_value(self.value_type),
                            "non_none_count": ModelSchemaValue.from_value(
                                str(non_none_count)
                            ),
                            "expected_value": ModelSchemaValue.from_value(
                                self.value_type
                            ),
                        }
                    ),
                )

            # Validate that the correct value is set for the type
            expected_value = values_map[self.value_type]
            if expected_value is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Required value for type '{self.value_type}' is None",
                    details=ModelErrorContext.with_context(
                        {
                            "value_type": ModelSchemaValue.from_value(self.value_type),
                            "required_field": ModelSchemaValue.from_value(
                                f"{self.value_type}_value"
                            ),
                        }
                    ),
                )

        return self

    @classmethod
    def from_string(cls, value: str, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from string."""
        return cls(
            value_type="string",
            string_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_integer(cls, value: int, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from integer."""
        return cls(
            value_type="integer",
            integer_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from float."""
        return cls(
            value_type="float",
            float_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_boolean(cls, value: bool, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from boolean."""
        return cls(
            value_type="boolean",
            boolean_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_dict_value(
        cls, value: dict[str, Any], source: str | None = None
    ) -> ModelFlexibleValue:
        """Create flexible value wrapping a dictionary value (not deserializing model fields)."""
        return cls(
            value_type="dict",
            dict_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_list(
        cls, value: list[Any], source: str | None = None
    ) -> ModelFlexibleValue:
        """Create flexible value from list."""
        return cls(
            value_type="list",
            list_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_uuid(cls, value: UUID, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from UUID."""
        return cls(
            value_type="uuid",
            uuid_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_none(cls, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value representing None."""
        return cls(
            value_type="none",
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_any(cls, value: Any, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from any supported type with automatic detection."""
        if value is None:
            return cls.from_none(source)
        if isinstance(value, str):
            return cls.from_string(value, source)
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.from_boolean(value, source)
        if isinstance(value, int):
            return cls.from_integer(value, source)
        if isinstance(value, float):
            return cls.from_float(value, source)
        if isinstance(value, dict):
            return cls.from_dict_value(value, source)
        if isinstance(value, list):
            return cls.from_list(value, source)
        if isinstance(value, UUID):
            return cls.from_uuid(value, source)
        # Fallback: convert unsupported types to string
        return cls.from_string(str(value), source)

    def get_value(self) -> Any:
        """Get the actual value with proper type."""
        if self.value_type == "string":
            return self.string_value
        if self.value_type == "integer":
            return self.integer_value
        if self.value_type == "float":
            return self.float_value
        if self.value_type == "boolean":
            return self.boolean_value
        if self.value_type == "dict":
            return self.dict_value
        if self.value_type == "list":
            return self.list_value
        if self.value_type == "uuid":
            return self.uuid_value
        if self.value_type == "none":
            return None
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown value_type: {self.value_type}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(self.value_type),
                    "supported_types": ModelSchemaValue.from_value(
                        "string, integer, float, boolean, dict, list, uuid, none",
                    ),
                }
            ),
        )

    def get_python_type(self) -> type:
        """Get the Python type of the stored value."""
        type_map = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "dict": dict,
            "list": list,
            "uuid": UUID,
            "none": type(None),
        }
        return type_map[self.value_type]

    def is_none(self) -> bool:
        """Check if the value represents None."""
        return self.value_type == "none"

    def is_primitive(self) -> bool:
        """Check if the value is a primitive type (string, int, float, bool)."""
        return self.value_type in ["string", "integer", "float", "boolean"]

    def is_collection(self) -> bool:
        """Check if the value is a collection type (dict, list)."""
        return self.value_type in ["dict", "list"]

    def to_schema_value(self) -> ModelSchemaValue:
        """Convert to ModelSchemaValue."""
        value = self.get_value()
        return ModelSchemaValue.from_value(value)

    def compare_value(self, other: ModelFlexibleValue | Any) -> bool:
        """Compare with another flexible value or raw value."""
        if isinstance(other, ModelFlexibleValue):
            return (
                self.value_type == other.value_type
                and self.get_value() == other.get_value()
            )
        return bool(self.get_value() == other)

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, ModelFlexibleValue):
            return self.compare_value(other)
        return bool(self.get_value() == other)

    def __str__(self) -> str:
        """String representation."""
        value = self.get_value()
        return f"FlexibleValue({self.value_type}: {value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ModelFlexibleValue(value_type='{self.value_type}', "
            f"value={self.get_value()}, source='{self.source}')"
        )


# Export the model
__all__ = ["ModelFlexibleValue"]
