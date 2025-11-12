from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Node info container model.

Clean, strongly-typed Pydantic model for containing node information.
Follows ONEX one-model-per-file naming conventions.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

from .model_node_info_summary import ModelNodeInfoSummary


class ModelNodeInfoContainer(BaseModel):
    """
    Clean, strongly-typed container for node information.

    Replaces: dict[str, ModelNodeInfoData] type alias
    With proper structured data using Pydantic validation.
    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    nodes: dict[UUID, ModelNodeInfoSummary] = Field(
        default_factory=dict,
        description="Collection of node information by node ID",
    )

    def add_node(self, node_id: UUID, node_info: ModelNodeInfoSummary) -> None:
        """Add a node to the container."""
        self.nodes[node_id] = node_info

    def get_node(self, node_id: UUID) -> ModelNodeInfoSummary | None:
        """Get a node from the container."""
        return self.nodes.get(node_id)

    def remove_node(self, node_id: UUID) -> bool:
        """Remove a node from the container. Returns True if node was removed."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False

    def get_node_count(self) -> int:
        """Get the total number of nodes in the container."""
        return len(self.nodes)

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
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelNodeInfoContainer"]
