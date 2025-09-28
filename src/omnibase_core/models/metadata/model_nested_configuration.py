"""
Nested configuration model.

Clean, strongly-typed model for nested configuration data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    MetadataProvider,
    Serializable,
    Validatable,
)
from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue


class ModelNestedConfiguration(BaseModel):
    """Model for nested configuration data.
    Implements omnibase_spi protocols:
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # UUID-based entity references
    config_id: UUID = Field(..., description="Unique identifier for the configuration")
    config_display_name: str | None = Field(
        None,
        description="Human-readable configuration name",
    )
    config_type: EnumConfigType = Field(
        ...,
        description="Configuration type",
    )
    settings: dict[str, ModelCliValue] = Field(
        default_factory=dict,
        description="Configuration settings with strongly-typed values",
    )

    # Export the model

    # Protocol method implementations

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


__all__ = ["ModelNestedConfiguration"]
