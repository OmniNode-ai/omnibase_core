"""
Metadata value model.

Type-safe metadata value container that replaces Union[str, int, float, bool]
with structured validation and proper type handling for metadata fields.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_cli_value_type import EnumCliValueType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Use object for internal storage with field validator ensuring proper types
# This avoids primitive union violations while maintaining type safety through validation


class ModelMetadataValue(BaseModel):
    """
    Type-safe metadata value container.

    Replaces Union[str, int, float, bool] with structured value storage
    that maintains type information for metadata fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Value storage with type tracking - uses object with validator for type safety
    value: object = Field(description="The actual metadata value")

    value_type: EnumCliValueType = Field(description="Type of the stored value")

    # Metadata
    is_validated: bool = Field(
        default=False, description="Whether value has been validated"
    )

    source: str | None = Field(default=None, description="Source of the metadata value")

    @model_validator(mode="after")
    def validate_value_type(self) -> ModelMetadataValue:
        """Validate that value matches its declared type."""
        value_type = self.value_type

        # Type validation based on declared type
        if value_type == EnumCliValueType.STRING and not isinstance(self.value, str):
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
                    }
                ),
            )
        if value_type == EnumCliValueType.INTEGER and not isinstance(self.value, int):
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
                    }
                ),
            )
        if value_type == EnumCliValueType.FLOAT and not isinstance(
            self.value, (int, float)
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be numeric, got {type(self.value)}",
                details=ModelErrorContext.with_context(
                    {
                        "expected_type": ModelSchemaValue.from_value("float"),
                        "actual_type": ModelSchemaValue.from_value(
                            str(type(self.value))
                        ),
                        "value": ModelSchemaValue.from_value(str(self.value)),
                    }
                ),
            )
        if value_type == EnumCliValueType.BOOLEAN and not isinstance(self.value, bool):
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
                    }
                ),
            )

        return self

    @classmethod
    def from_string(cls, value: str, source: str | None = None) -> ModelMetadataValue:
        """Create metadata value from string."""
        return cls(
            value=value,
            value_type=EnumCliValueType.STRING,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_int(cls, value: int, source: str | None = None) -> ModelMetadataValue:
        """Create metadata value from integer."""
        return cls(
            value=value,
            value_type=EnumCliValueType.INTEGER,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelMetadataValue:
        """Create metadata value from float."""
        return cls(
            value=value,
            value_type=EnumCliValueType.FLOAT,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_bool(cls, value: bool, source: str | None = None) -> ModelMetadataValue:
        """Create metadata value from boolean."""
        return cls(
            value=value,
            value_type=EnumCliValueType.BOOLEAN,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_any(cls, value: object, source: str | None = None) -> ModelMetadataValue:
        """Create metadata value from any supported type."""
        if isinstance(value, str):
            return cls.from_string(value, source)
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return cls.from_bool(value, source)
        if isinstance(value, int):
            return cls.from_int(value, source)
        if isinstance(value, float):
            return cls.from_float(value, source)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported value type: {type(value)}",
            details=ModelErrorContext.with_context(
                {
                    "supported_types": ModelSchemaValue.from_value(
                        "str, int, float, bool"
                    ),
                    "actual_type": ModelSchemaValue.from_value(str(type(value))),
                    "value": ModelSchemaValue.from_value(str(value)),
                }
            ),
        )

    def as_string(self) -> str:
        """Get value as string."""
        if self.value_type == EnumCliValueType.STRING:
            return str(self.value)
        return str(self.value)

    def as_int(self) -> int:
        """Get value as integer."""
        if self.value_type == EnumCliValueType.INTEGER:
            if not isinstance(self.value, (int, float, str)):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Expected numeric or string type, got {type(self.value)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_types": ModelSchemaValue.from_value(
                                "int, float, str"
                            ),
                            "actual_type": ModelSchemaValue.from_value(
                                str(type(self.value))
                            ),
                            "value": ModelSchemaValue.from_value(str(self.value)),
                        }
                    ),
                )
            return int(self.value)
        if isinstance(self.value, (int, float)):
            return int(self.value)
        if isinstance(self.value, str):
            try:
                return int(self.value)
            except ValueError:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Cannot convert string '{self.value}' to int",
                    details=ModelErrorContext.with_context(
                        {
                            "source_type": ModelSchemaValue.from_value("str"),
                            "target_type": ModelSchemaValue.from_value("int"),
                            "value": ModelSchemaValue.from_value(str(self.value)),
                        }
                    ),
                )
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to int",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("int"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                }
            ),
        )

    def as_float(self) -> float:
        """Get value as float."""
        if self.value_type in (EnumCliValueType.FLOAT, EnumCliValueType.INTEGER):
            if not isinstance(self.value, (int, float, str)):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Expected numeric or string type, got {type(self.value)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_types": ModelSchemaValue.from_value(
                                "int, float, str"
                            ),
                            "actual_type": ModelSchemaValue.from_value(
                                str(type(self.value))
                            ),
                            "value": ModelSchemaValue.from_value(str(self.value)),
                        }
                    ),
                )
            return float(self.value)
        if isinstance(self.value, (int, float)):
            return float(self.value)
        if isinstance(self.value, str):
            try:
                return float(self.value)
            except ValueError:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Cannot convert string '{self.value}' to float",
                    details=ModelErrorContext.with_context(
                        {
                            "source_type": ModelSchemaValue.from_value("str"),
                            "target_type": ModelSchemaValue.from_value("float"),
                            "value": ModelSchemaValue.from_value(str(self.value)),
                        }
                    ),
                )
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to float",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("float"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                }
            ),
        )

    def as_bool(self) -> bool:
        """Get value as boolean."""
        if self.value_type == EnumCliValueType.BOOLEAN:
            return bool(self.value)
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "1", "yes", "on")
        return bool(self.value)

    def to_python_value(self) -> object:
        """Get the underlying Python value."""
        return self.value

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> dict[str, object]:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata: dict[str, object] = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, object]) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            # Set metadata with runtime validation for type safety
            for key, value in metadata.items():
                if hasattr(self, key) and isinstance(
                    value, (str, int, float, bool, dict, list)
                ):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelMetadataValue"]
