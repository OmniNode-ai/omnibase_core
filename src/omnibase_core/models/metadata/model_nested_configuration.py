"""
Nested configuration model.

Clean, strongly-typed model for nested configuration data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNestedConfiguration(BaseModel):
    """Model for nested configuration data.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # UUID-based entity references
    config_id: UUID = Field(
        default=..., description="Unique identifier for the configuration"
    )
    config_display_name: str | None = Field(
        default=None,
        description="Human-readable configuration name",
    )
    config_type: EnumConfigType = Field(
        default=...,
        description="Configuration type",
    )
    settings: dict[str, ModelValue] = Field(
        default_factory=dict,
        description="Configuration settings with strongly-typed values",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        if self.config_display_name:
            result["name"] = self.config_display_name
        result["metadata"] = {
            "config_id": str(self.config_id),
            "config_type": self.config_type.value,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If metadata setting logic fails
        """
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> TypedDictSerializedModel:
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


__all__ = ["ModelNestedConfiguration"]
