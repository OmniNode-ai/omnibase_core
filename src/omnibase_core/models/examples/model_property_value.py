"""
Property value model.

Type-safe property value container that replaces broad Union types
with structured validation and proper type handling.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_property_type import EnumPropertyType
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Use object type to avoid primitive soup union anti-pattern.
# Type safety is ensured through discriminated union with EnumPropertyType discriminator
# and runtime validation in the field validator.
PropertyValueType = object

# Additional type aliases for enhanced type safety
StringPropertyType = str


class ModelPropertyValue(BaseModel):
    """
    Type-safe property value container.

    Uses discriminated union pattern with runtime validation to ensure
    type safety while avoiding overly broad Union types.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Value storage with runtime validation - discriminated union with type safety
    value: PropertyValueType = Field(
        description="The actual property value - validated against value_type",
    )

    value_type: EnumPropertyType = Field(
        description="Type discriminator for the stored value",
    )

    # Metadata
    is_validated: bool = Field(
        default=False,
        description="Whether value has been validated",
    )

    source: str | None = Field(
        default=None,
        description="Source of the property value",
    )

    @model_validator(mode="after")
    def validate_value_type(self) -> ModelPropertyValue:
        """Validate that value matches its declared type."""
        value_type = self.value_type

        # Type validation based on declared type
        if value_type == EnumPropertyType.STRING and not isinstance(self.value, str):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be string, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("string"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        if value_type == EnumPropertyType.INTEGER and not isinstance(self.value, int):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be integer, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("integer"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        if value_type == EnumPropertyType.FLOAT and not isinstance(
            self.value,
            (int, float),
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be float, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("float"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        if value_type == EnumPropertyType.BOOLEAN and not isinstance(self.value, bool):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be boolean, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("boolean"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        if value_type in (
            EnumPropertyType.STRING_LIST,
            EnumPropertyType.INTEGER_LIST,
            EnumPropertyType.FLOAT_LIST,
        ) and not isinstance(self.value, list):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be list[Any], got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("list[Any]"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        if value_type == EnumPropertyType.DATETIME and not isinstance(
            self.value,
            datetime,
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be datetime, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("datetime"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )
        if value_type == EnumPropertyType.UUID and not isinstance(
            self.value, (UUID, str)
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be UUID or string, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("uuid"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    },
                ),
            )

        return self

    @classmethod
    def from_string(cls, value: str, source: str | None = None) -> ModelPropertyValue:
        """Create property value from string."""
        return cls(
            value=value,
            value_type=EnumPropertyType.STRING,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_int(cls, value: int, source: str | None = None) -> ModelPropertyValue:
        """Create property value from integer."""
        return cls(
            value=value,
            value_type=EnumPropertyType.INTEGER,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelPropertyValue:
        """Create property value from float."""
        return cls(
            value=value,
            value_type=EnumPropertyType.FLOAT,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_bool(cls, value: bool, source: str | None = None) -> ModelPropertyValue:
        """Create property value from boolean."""
        return cls(
            value=value,
            value_type=EnumPropertyType.BOOLEAN,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_string_list(
        cls,
        value: list[str],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from string list[Any]."""
        return cls(
            value=value,
            value_type=EnumPropertyType.STRING_LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_int_list(
        cls,
        value: list[int],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from integer list[Any]."""
        return cls(
            value=value,
            value_type=EnumPropertyType.INTEGER_LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float_list(
        cls,
        value: list[float],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from float list[Any]."""
        return cls(
            value=value,
            value_type=EnumPropertyType.FLOAT_LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_datetime(
        cls,
        value: datetime,
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from datetime."""
        return cls(
            value=value,
            value_type=EnumPropertyType.DATETIME,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_uuid(
        cls,
        value: UUID,
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from UUID."""
        return cls(
            value=value,
            value_type=EnumPropertyType.UUID,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_uuid_string(
        cls,
        value: str,
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from UUID string representation."""
        try:
            uuid_value = UUID(value)
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid UUID string format: {value}",
                details=ModelErrorContext.with_context(
                    {
                        "input_value": ModelSchemaValue.from_value(value),
                        "error": ModelSchemaValue.from_value(str(e)),
                    },
                ),
            ) from e

        return cls(
            value=uuid_value,
            value_type=EnumPropertyType.UUID,
            source=source,
            is_validated=True,
        )

    def as_string(self) -> str:
        """Get value as string."""
        if self.value_type == EnumPropertyType.STRING:
            return str(self.value)
        return str(self.value)

    def as_int(self) -> int:
        """Get value as integer."""
        if self.value_type == EnumPropertyType.INTEGER:
            assert isinstance(
                self.value,
                (int, float, str),
            ), f"Expected numeric or string type, got {type(self.value)}"
            return int(self.value)
        if isinstance(self.value, (int, float)):
            return int(self.value)
        if isinstance(self.value, str):
            return int(self.value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to int",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("int"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    def as_float(self) -> float:
        """Get value as float."""
        if self.value_type in (EnumPropertyType.FLOAT, EnumPropertyType.INTEGER):
            assert isinstance(
                self.value,
                (int, float, str),
            ), f"Expected numeric or string type, got {type(self.value)}"
            return float(self.value)
        if isinstance(self.value, str):
            return float(self.value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to float",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("float"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    def as_bool(self) -> bool:
        """Get value as boolean."""
        if self.value_type == EnumPropertyType.BOOLEAN:
            return bool(self.value)
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "1", "yes", "on")
        return bool(self.value)

    def as_list(self) -> list[object]:
        """Get value as list[Any]."""
        if self.value_type in (
            EnumPropertyType.STRING_LIST,
            EnumPropertyType.INTEGER_LIST,
            EnumPropertyType.FLOAT_LIST,
        ):
            assert isinstance(
                self.value,
                list,
            ), f"Expected list type, got {type(self.value)}"
            return list(self.value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to list[Any]",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("list[Any]"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    def as_uuid(self) -> UUID:
        """Get value as UUID."""
        if self.value_type == EnumPropertyType.UUID:
            if isinstance(self.value, UUID):
                return self.value
            assert isinstance(
                self.value,
                str,
            ), f"Expected string type for UUID conversion, got {type(self.value)}"
            return UUID(self.value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to UUID",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("UUID"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


__all__ = ["ModelPropertyValue"]
