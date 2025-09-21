"""
Field identity sub-model.

Part of the metadata field info restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field


class ModelFieldIdentity(BaseModel):
    """Identity information for metadata fields."""

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
        identity_name = self.identity_display_name or f"identity_{str(self.identity_id)[:8]}"
        field_name = self.field_display_name or f"field_{str(self.field_id)[:8]}"
        return (
            identity_name.upper() == name.upper()
            or field_name.lower() == name.lower()
        )

    @property
    def name(self) -> str:
        """Backward compatibility property for name."""
        return self.identity_display_name or f"identity_{str(self.identity_id)[:8]}"

    @name.setter
    def name(self, value: str) -> None:
        """Backward compatibility setter for name."""
        import hashlib
        identity_hash = hashlib.sha256(value.encode()).hexdigest()
        self.identity_id = UUID(f"{identity_hash[:8]}-{identity_hash[8:12]}-{identity_hash[12:16]}-{identity_hash[16:20]}-{identity_hash[20:32]}")
        self.identity_display_name = value

    @property
    def field_name(self) -> str:
        """Backward compatibility property for field_name."""
        return self.field_display_name or f"field_{str(self.field_id)[:8]}"

    @field_name.setter
    def field_name(self, value: str) -> None:
        """Backward compatibility setter for field_name."""
        import hashlib
        field_hash = hashlib.sha256(value.encode()).hexdigest()
        self.field_id = UUID(f"{field_hash[:8]}-{field_hash[8:12]}-{field_hash[12:16]}-{field_hash[16:20]}-{field_hash[20:32]}")
        self.field_display_name = value


# Export the model
__all__ = ["ModelFieldIdentity"]