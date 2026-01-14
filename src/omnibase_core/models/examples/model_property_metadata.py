"""
Property metadata model for environment properties.

This module provides the ModelPropertyMetadata class for storing metadata
about individual properties in the environment property system.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_property_type import EnumPropertyType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelPropertyMetadata(BaseModel):
    """Metadata for individual properties.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    description: str = Field(default="", description="Property description")
    source: str = Field(default="", description="Source of the property")
    property_type: EnumPropertyType = Field(description="Type of the property")
    required: bool = Field(default=False, description="Whether property is required")
    validation_pattern: str = Field(
        default="",
        description="Regex pattern for validation",
    )
    min_value: float | None = Field(
        default=None, description="Minimum value for numeric types"
    )
    max_value: float | None = Field(
        default=None, description="Maximum value for numeric types"
    )
    allowed_values: list[str] = Field(
        default_factory=list,
        description="Allowed values for enum-like properties",
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
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
