"""
Field validation rules sub-model.

Part of the metadata field info restructuring to reduce string field violations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelFieldValidationRules(BaseModel):
    """Validation rules for metadata fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Validation constraints (non-string where possible)
    validation_pattern: str | None = Field(
        default=None,
        description="Regex pattern for string validation",
    )

    min_length: int | None = Field(
        default=None,
        description="Minimum length for string fields",
    )

    max_length: int | None = Field(
        default=None,
        description="Maximum length for string fields",
    )

    min_value: ModelNumericValue | None = Field(
        default=None,
        description="Minimum value for numeric fields",
    )

    max_value: ModelNumericValue | None = Field(
        default=None,
        description="Maximum value for numeric fields",
    )

    allow_empty: bool = Field(
        default=True,
        description="Whether empty values are allowed",
    )

    def has_string_validation(self) -> bool:
        """Check if string validation rules are defined."""
        return (
            self.validation_pattern is not None
            or self.min_length is not None
            or self.max_length is not None
        )

    def has_numeric_validation(self) -> bool:
        """Check if numeric validation rules are defined."""
        return self.min_value is not None or self.max_value is not None

    def is_valid_string(self, value: str) -> bool:
        """Validate a string value against the rules."""
        if not self.allow_empty and not value:
            return False

        if self.min_length is not None and len(value) < self.min_length:
            return False

        if self.max_length is not None and len(value) > self.max_length:
            return False

        if self.validation_pattern is not None:
            import re

            try:
                return bool(re.match(self.validation_pattern, value))
            except re.error:
                return False

        return True

    def is_valid_numeric(self, value: ModelNumericValue) -> bool:
        """Validate a numeric value against the rules."""
        # Value is ModelNumericValue type
        comparison_value = value.to_python_value()

        if (
            self.min_value is not None
            and comparison_value < self.min_value.to_python_value()
        ):
            return False

        if (
            self.max_value is not None
            and comparison_value > self.max_value.to_python_value()
        ):
            return False

        return True

    def set_min_value(self, value: ModelNumericValue) -> None:
        """Set minimum value validation rule."""
        # Value is ModelNumericValue type
        self.min_value = value

    def set_max_value(self, value: ModelNumericValue) -> None:
        """Set maximum value validation rule."""
        # Value is ModelNumericValue type
        self.max_value = value

    def get_min_value(self) -> ModelNumericValue | None:
        """Get minimum value as ModelNumericValue."""
        return self.min_value

    def get_max_value(self) -> ModelNumericValue | None:
        """Get maximum value as ModelNumericValue."""
        return self.max_value

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        from omnibase_core.types.type_serializable_value import SerializableValue

        result: TypedDictMetadataDict = {}
        metadata_dict: dict[str, SerializableValue] = {
            "allow_empty": self.allow_empty,
            "has_string_validation": self.has_string_validation(),
            "has_numeric_validation": self.has_numeric_validation(),
        }
        if self.validation_pattern is not None:
            metadata_dict["validation_pattern"] = self.validation_pattern
        if self.min_length is not None:
            metadata_dict["min_length"] = self.min_length
        if self.max_length is not None:
            metadata_dict["max_length"] = self.max_length
        result["metadata"] = metadata_dict
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
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


__all__ = ["ModelFieldValidationRules"]
