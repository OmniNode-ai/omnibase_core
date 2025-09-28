"""
Node information summary model.

Clean, strongly-typed replacement for node information dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    Identifiable,
    MetadataProvider,
    Serializable,
    Validatable,
)

from .model_node_capabilities_summary import ModelNodeCapabilitiesSummary
from .model_node_configuration_summary import ModelNodeConfigurationSummary
from .model_node_core_info_summary import ModelNodeCoreInfoSummary


class ModelNodeInformationSummary(BaseModel):
    """
    Clean, strongly-typed model replacing node information dict return types.

    Eliminates: dict[str, Any]

    With proper structured data using specific field types.
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    core_info: ModelNodeCoreInfoSummary = Field(
        description="Core node information summary",
    )
    capabilities: ModelNodeCapabilitiesSummary = Field(
        description="Node capabilities summary",
    )
    configuration: ModelNodeConfigurationSummary = Field(
        description="Node configuration summary",
    )
    is_fully_configured: bool = Field(description="Whether node is fully configured")

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


__all__ = ["ModelNodeInformationSummary"]
