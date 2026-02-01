"""
Metadata value model.

Type-safe metadata value container that replaces Union[str, int, float, bool]
with structured validation and proper type handling for metadata fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_cli_value_type import EnumCliValueType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """
        Get metadata as dictionary for ProtocolMetadataProvider protocol.

        Returns a TypedDictMetadataDict containing type-safe metadata value
        information. This model does not map to top-level name/version/description
        fields as it represents a primitive value container rather than a named entity.

        Returns:
            TypedDictMetadataDict with the following structure:
            - "metadata": Dict containing:
                - "value_type": String representation of EnumCliValueType
                  (e.g., "STRING", "INTEGER", "FLOAT", "BOOLEAN")
                - "is_validated": Boolean indicating if value passed validation
                - "source": Optional string indicating value origin (only if set)

        Example:
            >>> value = ModelMetadataValue.from_string("test", source="config")
            >>> metadata = value.get_metadata()
            >>> metadata["metadata"]["value_type"]
            'STRING'
            >>> metadata["metadata"]["is_validated"]
            True
            >>> metadata["metadata"]["source"]
            'config'
        """
        result: TypedDictMetadataDict = {}
        result["metadata"] = {
            "value_type": self.value_type.value,
            "is_validated": self.is_validated,
        }
        if self.source is not None:
            result["metadata"]["source"] = self.source
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """
        Set metadata from dictionary for ProtocolMetadataProvider protocol.

        Symmetric with get_metadata() - extracts model-specific data from the
        nested 'metadata' key in the TypedDictMetadataDict structure.

        Args:
            metadata: TypedDictMetadataDict containing metadata to apply.
                Expected structure matches get_metadata() output:
                - "metadata": Dict containing:
                    - "value_type": String representation of EnumCliValueType
                    - "is_validated": Boolean
                    - "source": Optional string

        Returns:
            True if metadata was successfully applied.

        Raises:
            ModelOnexError: If metadata application fails.

        Example:
            >>> value = ModelMetadataValue.from_string("test")
            >>> original = value.get_metadata()
            >>> new_value = ModelMetadataValue.from_int(42)
            >>> new_value.set_metadata(original)  # Apply original's metadata
            True
        """
        try:
            # Extract model-specific data from nested 'metadata' dict
            # This is symmetric with get_metadata() which places data there
            if "metadata" in metadata:
                inner_metadata = metadata["metadata"]
                if isinstance(inner_metadata, dict):
                    # Handle value_type - convert string back to enum if needed
                    if "value_type" in inner_metadata:
                        value_type_val = inner_metadata["value_type"]
                        if isinstance(value_type_val, str):
                            self.value_type = EnumCliValueType(value_type_val)
                        # Note: EnumCliValueType is not in SerializableValue so we only handle str

                    # Handle is_validated
                    if "is_validated" in inner_metadata:
                        is_val = inner_metadata["is_validated"]
                        if isinstance(is_val, bool):
                            self.is_validated = is_val

                    # Handle source
                    if "source" in inner_metadata:
                        source_val = inner_metadata["source"]
                        if isinstance(source_val, str) or source_val is None:
                            self.source = source_val
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
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
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelMetadataValue"]
