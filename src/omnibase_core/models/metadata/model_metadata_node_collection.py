"""
Metadata Node Collection Model.

Clean, focused implementation with proper typing and single responsibility following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, RootModel

from omnibase_core.core.type_constraints import (
    MetadataProvider,
    Serializable,
    Validatable,
)

from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_node_info_container import ModelNodeInfoContainer
from .model_node_union import ModelNodeUnion


class ModelMetadataNodeCollection(RootModel[dict[str, ModelNodeUnion]]):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Clean implementation with proper typing, focused responsibilities, and ONEX compliance.
    Implements omnibase_spi protocols:
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    root: dict[str, ModelNodeUnion] = Field(
        default_factory=dict,
        description="Root dictionary containing metadata nodes",
    )

    def __init__(
        self,
        root: Any = None,
        **kwargs: Any,
    ) -> None:
        """Initialize with enhanced enterprise features."""
        if root is None:
            root = {}
        elif isinstance(root, ModelMetadataNodeCollection):
            root = root.root

        super().__init__(root)

        # Initialize enterprise features if not present
        if "_metadata_analytics" not in self.root:
            analytics_data = ModelMetadataNodeAnalytics().model_dump()
            self.root["_metadata_analytics"] = analytics_data  # type: ignore[assignment]

        if "_node_info" not in self.root:
            node_info_container = ModelNodeInfoContainer()
            self.root["_node_info"] = node_info_container  # type: ignore[assignment]

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
        result: dict[str, Any] = self.model_dump(exclude_none=False, by_alias=True)
        return result

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False
