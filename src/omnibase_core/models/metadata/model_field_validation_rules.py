from __future__ import annotations

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Field validation rules sub-model.

Part of the metadata field info restructuring to reduce string field violations.
"""


from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_numeric_value import ModelNumericValue


class ModelFieldValidationRules(BaseModel):
    """Validation rules for metadata fields.
    Implements omnibase_spi protocols:
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
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
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelFieldValidationRules"]
