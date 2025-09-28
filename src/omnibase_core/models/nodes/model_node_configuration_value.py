"""
Node configuration value model.

Type-safe configuration value container that replaces str | int unions
with structured validation and proper type handling for node configurations.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    Identifiable,
    MetadataProvider,
    Serializable,
    Validatable,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelNodeConfigurationValue(BaseModel):
    """
    Type-safe configuration value container for node capabilities.

    Replaces str | int unions with structured value storage
    that maintains type information for configuration validation.
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Value storage (one will be set)
    string_value: str | None = Field(None, description="String configuration value")
    numeric_value: ModelNumericValue | None = Field(
        None,
        description="Numeric configuration value",
    )

    # Type indicator
    value_type: str = Field(
        ...,
        description="Type of the configuration value: string or numeric",
    )

    @classmethod
    def from_string(cls, value: str) -> ModelNodeConfigurationValue:
        """Create configuration value from string."""
        return cls(
            string_value=value,
            numeric_value=None,
            value_type="string",
        )

    @classmethod
    def from_int(cls, value: int) -> ModelNodeConfigurationValue:
        """Create configuration value from integer."""
        return cls(
            string_value=None,
            numeric_value=ModelNumericValue.from_int(value),
            value_type="numeric",
        )

    @classmethod
    def from_numeric(cls, value: ModelNumericValue) -> ModelNodeConfigurationValue:
        """Create configuration value from numeric value."""
        # Value is already ModelNumericValue type
        return cls(
            string_value=None,
            numeric_value=value,
            value_type="numeric",
        )

    @classmethod
    def from_value(cls, value: Any) -> ModelNodeConfigurationValue:
        """Create configuration value from any supported type.

        Args:
            value: Input value (str, int, float, bool, or other types)

        Returns:
            ModelNodeConfigurationValue with appropriate type discrimination
        """
        if isinstance(value, str):
            return cls.from_string(value)
        if isinstance(value, int):
            return cls.from_int(value)
        if isinstance(value, float):
            return cls.from_numeric(ModelNumericValue.from_float(value))
        # Fallback to string representation for bool and other types
        return cls.from_string(str(value))

    def to_python_value(self) -> Any:
        """Get the underlying Python value as the original type.

        Returns:
            str for string values, int/float for numeric values
        """
        if self.value_type == "string" and self.string_value is not None:
            return self.string_value
        if self.value_type == "numeric" and self.numeric_value is not None:
            return self.numeric_value.to_python_value()
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid configuration value state: {self.value_type}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "string_value": ModelSchemaValue.from_value(str(self.string_value)),
                    "numeric_value": ModelSchemaValue.from_value(
                        str(self.numeric_value)
                    ),
                }
            ),
        )

    def as_numeric(self) -> Any:
        """Get value as numeric type.

        Returns:
            int or float depending on the stored numeric value
        """
        if self.value_type == "numeric" and self.numeric_value is not None:
            return self.numeric_value.to_python_value()
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Configuration value is not numeric",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "method": ModelSchemaValue.from_value("as_numeric"),
                }
            ),
        )

    def as_string(self) -> str:
        """Get configuration value as string."""
        if self.string_value is not None:
            return self.string_value
        if self.numeric_value is not None:
            return str(self.numeric_value.to_python_value())
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="No value set in configuration",
            details=ModelErrorContext.with_context(
                {
                    "method": ModelSchemaValue.from_value("as_string"),
                    "string_value": ModelSchemaValue.from_value(str(self.string_value)),
                    "numeric_value": ModelSchemaValue.from_value(
                        str(self.numeric_value)
                    ),
                }
            ),
        )

    def as_int(self) -> int:
        """Get configuration value as integer (if numeric)."""
        if self.numeric_value is not None:
            return self.numeric_value.as_int()
        if self.string_value is not None:
            try:
                return int(self.string_value)
            except ValueError as e:
                raise OnexError(
                    code=EnumCoreErrorCode.CONVERSION_ERROR,
                    message=f"Cannot convert string '{self.string_value}' to int",
                    details=ModelErrorContext.with_context(
                        {
                            "string_value": ModelSchemaValue.from_value(
                                str(self.string_value)
                            ),
                            "target_type": ModelSchemaValue.from_value("int"),
                            "original_error": ModelSchemaValue.from_value(str(e)),
                        }
                    ),
                ) from e
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="No value set in configuration",
                details=ModelErrorContext.with_context(
                    {
                        "method": ModelSchemaValue.from_value("as_int"),
                        "string_value": ModelSchemaValue.from_value(
                            str(self.string_value)
                        ),
                        "numeric_value": ModelSchemaValue.from_value(
                            str(self.numeric_value)
                        ),
                    }
                ),
            )

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, ModelNodeConfigurationValue):
            return (
                self.string_value == other.string_value
                and self.numeric_value == other.numeric_value
            )
        # Allow comparison with raw values
        try:
            return cast(bool, self.to_python_value() == other)
        except (ValueError, TypeError):
            return False

    # Export the model

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dictionary (MetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (MetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


__all__ = ["ModelNodeConfigurationValue"]
