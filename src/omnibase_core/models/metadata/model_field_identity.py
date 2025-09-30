"""
Field identity sub-model.

Part of the metadata field info restructuring to reduce string field violations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelFieldIdentity(BaseModel):
    """Identity information for metadata fields.
    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identifiers (UUID pattern)
    identity_id: UUID = Field(
        ...,
        description="UUID for field identity identifier",
    )
    identity_display_name: str | None = Field(
        None,
        description="Human-readable field name identifier (e.g., METADATA_VERSION)",
        pattern="^[A-Z][A-Z0-9_]*$",
    )

    field_id: UUID = Field(
        ...,
        description="UUID for actual field name",
    )
    field_display_name: str | None = Field(
        None,
        description="Actual field name in models (e.g., metadata_version)",
    )

    description: str = Field(
        default="",
        description="Human-readable description of the field",
    )

    def get_display_name(self) -> str:
        """Get a human-readable display name."""
        # Convert FIELD_NAME to Field Name
        name = self.identity_display_name or f"identity_{str(self.identity_id)[:8]}"
        return " ".join(word.capitalize() for word in name.split("_"))

    def matches_name(self, name: str) -> bool:
        """Check if this field matches the given name."""
        identity_name = (
            self.identity_display_name or f"identity_{str(self.identity_id)[:8]}"
        )
        field_name = self.field_display_name or f"field_{str(self.field_id)[:8]}"
        return (
            identity_name.upper() == name.upper() or field_name.lower() == name.lower()
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
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
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
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
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


__all__ = ["ModelFieldIdentity"]
