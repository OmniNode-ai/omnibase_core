"""
Flexible Value Model - Discriminated Union for Mixed Type Values.

Replaces dict[str, Any]| None, list[Any]| None, and other mixed-type unions
with structured discriminated union pattern for type safety.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_flexible_value_type import EnumFlexibleValueType
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_error_context import ModelErrorContext
from .model_schema_value import ModelSchemaValue

# Note: Previously had type aliases (FlexibleDictType, FlexibleListType, FlexibleValueType)
# These were removed to comply with ONEX strong typing standards.
# Now uses dict[str, ModelSchemaValue] for strong typing.


class ModelFlexibleValue(BaseModel):
    """
    Discriminated union for values that can be multiple types.

    Replaces lazy Union[str, dict[str, Any], list[Any], int, etc.] patterns with
    structured type safety and proper validation.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    value_type: EnumFlexibleValueType = Field(
        description="Type discriminator for value",
    )

    # Value storage (only one should be populated)
    string_value: str | None = None
    integer_value: int | None = None
    float_value: float | None = None
    boolean_value: bool | None = None
    dict_value: dict[str, ModelSchemaValue] | None = None
    list_value: list[ModelSchemaValue] | None = None
    uuid_value: UUID | None = None

    # Metadata
    source: str | None = Field(default=None, description="Source of the value")
    is_validated: bool = Field(
        default=False,
        description="Whether value has been validated",
    )

    @model_validator(mode="after")
    def validate_single_value(self) -> ModelFlexibleValue:
        """Ensure only one value is set based on type discriminator."""
        values_map = {
            EnumFlexibleValueType.STRING: self.string_value,
            EnumFlexibleValueType.INTEGER: self.integer_value,
            EnumFlexibleValueType.FLOAT: self.float_value,
            EnumFlexibleValueType.BOOLEAN: self.boolean_value,
            EnumFlexibleValueType.DICT: self.dict_value,
            EnumFlexibleValueType.LIST: self.list_value,
            EnumFlexibleValueType.UUID: self.uuid_value,
            EnumFlexibleValueType.NONE: None,
        }

        # Count non-None values
        non_none_count = sum(1 for v in values_map.values() if v is not None)

        # For "none" type, all values should be None
        if self.value_type == EnumFlexibleValueType.NONE:
            if non_none_count > 0:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="No values should be set when value_type is 'none'",
                    details=ModelErrorContext.with_context(
                        {
                            "value_type": ModelSchemaValue.from_value(self.value_type),
                            "non_none_count": ModelSchemaValue.from_value(
                                str(non_none_count),
                            ),
                        },
                    ),
                )
        else:
            # For other types, exactly one value should be set
            if non_none_count != 1:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Exactly one value must be set for value_type '{self.value_type}'",
                    details=ModelErrorContext.with_context(
                        {
                            "value_type": ModelSchemaValue.from_value(self.value_type),
                            "non_none_count": ModelSchemaValue.from_value(
                                str(non_none_count),
                            ),
                            "expected_value": ModelSchemaValue.from_value(
                                self.value_type,
                            ),
                        },
                    ),
                )

            # Validate that the correct value is set for the type
            expected_value = values_map[self.value_type]
            if expected_value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Required value for type '{self.value_type}' is None",
                    details=ModelErrorContext.with_context(
                        {
                            "value_type": ModelSchemaValue.from_value(self.value_type),
                            "required_field": ModelSchemaValue.from_value(
                                f"{self.value_type}_value",
                            ),
                        },
                    ),
                )

        return self

    @classmethod
    def from_string(cls, value: str, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from string."""
        return cls(
            value_type=EnumFlexibleValueType.STRING,
            string_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_integer(cls, value: int, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from integer."""
        return cls(
            value_type=EnumFlexibleValueType.INTEGER,
            integer_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from float."""
        return cls(
            value_type=EnumFlexibleValueType.FLOAT,
            float_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_boolean(cls, value: bool, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from boolean."""
        return cls(
            value_type=EnumFlexibleValueType.BOOLEAN,
            boolean_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_dict_value(
        cls,
        value: dict[str, ModelSchemaValue],
        source: str | None = None,
    ) -> ModelFlexibleValue:
        """Create flexible value from dictionary of ModelSchemaValue."""
        return cls(
            value_type=EnumFlexibleValueType.DICT,
            dict_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_raw_dict(
        cls,
        value: dict[str, object],
        source: str | None = None,
    ) -> ModelFlexibleValue:
        """Create flexible value from raw dictionary, converting to ModelSchemaValue format."""
        converted_value = {
            key: ModelSchemaValue.from_value(val) for key, val in value.items()
        }
        return cls.from_dict_value(converted_value, source)

    @classmethod
    def from_list(
        cls,
        value: list[object],
        source: str | None = None,
    ) -> ModelFlexibleValue:
        """Create flexible value from list[Any]."""
        return cls(
            value_type=EnumFlexibleValueType.LIST,
            list_value=[ModelSchemaValue.from_value(item) for item in value],
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_uuid(cls, value: UUID, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value from UUID."""
        return cls(
            value_type=EnumFlexibleValueType.UUID,
            uuid_value=value,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_none(cls, source: str | None = None) -> ModelFlexibleValue:
        """Create flexible value representing None."""
        return cls(
            value_type=EnumFlexibleValueType.NONE,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_any(cls, value: object, source: str | None = None) -> ModelFlexibleValue:
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
            return cls.from_raw_dict(value, source)
        if isinstance(value, list):
            return cls.from_list(value, source)
        if isinstance(value, UUID):
            return cls.from_uuid(value, source)
        # Fallback: convert unsupported types to string
        return cls.from_string(str(value), source)

    def get_value(self) -> object:
        """Get the actual value with proper type."""
        if self.value_type == EnumFlexibleValueType.STRING:
            return self.string_value
        if self.value_type == EnumFlexibleValueType.INTEGER:
            return self.integer_value
        if self.value_type == EnumFlexibleValueType.FLOAT:
            return self.float_value
        if self.value_type == EnumFlexibleValueType.BOOLEAN:
            return self.boolean_value
        if self.value_type == EnumFlexibleValueType.DICT:
            return self.dict_value
        if self.value_type == EnumFlexibleValueType.LIST:
            return [
                item.to_value()
                for item in (self.list_value if self.list_value is not None else [])
            ]
        if self.value_type == EnumFlexibleValueType.UUID:
            return self.uuid_value
        if self.value_type == EnumFlexibleValueType.NONE:
            return None
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown value_type: {self.value_type}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(self.value_type),
                    "supported_types": ModelSchemaValue.from_value(
                        "string, integer, float, boolean, dict[str, Any], list[Any], uuid, none",
                    ),
                },
            ),
        )

    def get_python_type(self) -> type:
        """Get the Python type of the stored value."""
        type_map: dict[EnumFlexibleValueType, type] = {
            EnumFlexibleValueType.STRING: str,
            EnumFlexibleValueType.INTEGER: int,
            EnumFlexibleValueType.FLOAT: float,
            EnumFlexibleValueType.BOOLEAN: bool,
            EnumFlexibleValueType.DICT: dict,
            EnumFlexibleValueType.LIST: list,
            EnumFlexibleValueType.UUID: UUID,
            EnumFlexibleValueType.NONE: type(None),
        }
        return type_map[self.value_type]

    def is_none(self) -> bool:
        """Check if the value represents None."""
        return self.value_type == EnumFlexibleValueType.NONE

    def is_primitive(self) -> bool:
        """Check if the value is a primitive type (string, int, float, bool)."""
        return self.value_type in [
            EnumFlexibleValueType.STRING,
            EnumFlexibleValueType.INTEGER,
            EnumFlexibleValueType.FLOAT,
            EnumFlexibleValueType.BOOLEAN,
        ]

    def is_collection(self) -> bool:
        """Check if the value is a collection type (dict[str, Any], list[Any])."""
        return self.value_type in [
            EnumFlexibleValueType.DICT,
            EnumFlexibleValueType.LIST,
        ]

    def to_schema_value(self) -> ModelSchemaValue:
        """Convert to ModelSchemaValue."""
        value = self.get_value()
        return ModelSchemaValue.from_value(value)

    def compare_value(self, other: object) -> bool:
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


__all__ = ["ModelFlexibleValue"]
