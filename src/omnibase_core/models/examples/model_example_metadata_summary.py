"""
Example metadata summary model.

This module provides the ModelExampleMetadataSummary class for clean
metadata summary following ONEX naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExampleMetadataSummary(BaseModel):
    """Clean model for metadata summary.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")
    version: ModelSemVer | None = Field(default=None, description="Metadata version")
    author_id: UUID | None = Field(default=None, description="UUID of the author")
    author_display_name: str | None = Field(
        default=None,
        description="Human-readable author name",
    )
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    custom_fields: dict[str, ModelMetadataValue] = Field(
        default_factory=dict,
        description="Custom metadata fields with type-safe values",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
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
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Returns True for well-constructed instances. Override in subclasses
        for custom validation logic.
        """
        # Basic validation - Pydantic handles field constraints
        # Override in specific models for custom validation
        return True


__all__ = ["ModelExampleMetadataSummary"]
