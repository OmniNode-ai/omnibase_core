from __future__ import annotations

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Metadata Node Collection Model.

Clean, focused implementation with proper typing and single responsibility following ONEX one-model-per-file architecture.
"""


from typing import Any

from pydantic import Field, RootModel

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_node_info_container import ModelNodeInfoContainer


class ModelMetadataNodeCollection(RootModel[dict[str, Any]]):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Clean implementation with proper typing, focused responsibilities, and ONEX compliance.
    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    root: dict[str, Any] = Field(
        default_factory=dict,
        description="Root dict[str, Any]ionary containing metadata nodes and analytics data",
    )

    def __init__(
        self,
        root: dict[str, Any] | None = None,
        **kwargs,
    ) -> None:
        """
        Initialize with enhanced enterprise features.

        Args:
            root: Initial root data - accepts dict[str, Any] or None

        Raises:
            ModelOnexError: If root is not of expected type (VALIDATION_ERROR)
        """
        # Runtime validation for type safety
        if root is None:
            validated_root: dict[str, Any] = {}
        elif isinstance(root, dict):
            # Validate dict[str, Any]structure if needed
            validated_root = root
        else:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"root must be dict[str, Any]or None, got {type(root).__name__}",
                details={
                    "received_type": type(root).__name__,
                    "expected_types": ["dict[str, Any]", "None"],
                    "parameter": "root",
                },
            )

        super().__init__(validated_root)

        # Initialize enterprise features if not present
        # Note: These special keys store model instances for analytics and info
        if "_metadata_analytics" not in validated_root:
            analytics_data = ModelMetadataNodeAnalytics()
            validated_root["_metadata_analytics"] = analytics_data

        if "_node_info" not in validated_root:
            node_info_container = ModelNodeInfoContainer()
            validated_root["_node_info"] = node_info_container

        # Update root after initialization
        self.root = validated_root

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
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
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            # fallback-ok: ProtocolMetadataProvider contract expects bool, not exceptions
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        result: dict[str, Any] = self.model_dump(exclude_none=False, by_alias=True)
        return result

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            # fallback-ok: ProtocolValidatable contract expects bool validation result, not exceptions
            return False
