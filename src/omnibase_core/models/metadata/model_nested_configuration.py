from __future__ import annotations

from pydantic import Field

"""
Nested configuration model.

Clean, strongly-typed model for nested configuration data.
Follows ONEX one-model-per-file naming conventions.
"""


from uuid import UUID

from pydantic import BaseModel

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata  # type: ignore[return-value]

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
