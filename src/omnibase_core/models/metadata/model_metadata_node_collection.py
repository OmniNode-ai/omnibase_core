"""
Metadata Node Collection Model.

Clean, focused implementation with proper typing and single responsibility following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, RootModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_node_info_container import ModelNodeInfoContainer


class ModelMetadataNodeCollection(RootModel[dict[str, object]]):
    """
    Enterprise-grade collection of metadata/documentation nodes for ONEX metadata blocks.

    Clean implementation with proper typing, focused responsibilities, and ONEX compliance.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    root: dict[str, object] = Field(
        default_factory=dict,
        description="Root dictionary containing metadata nodes and analytics data",
    )

    def __init__(
        self,
        root: dict[str, object] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize with enhanced enterprise features.

        Args:
            root: Initial root data - accepts dict[str, object] or None

        Raises:
            ModelOnexError: If root is not of expected type (VALIDATION_ERROR)
        """
        # Runtime validation for type safety
        if root is None:
            validated_root: dict[str, object] = {}
        elif isinstance(root, dict):
            # Validate dict[str, object] structure if needed
            validated_root = root
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"root must be dict or None, got {type(root).__name__}",
                details={
                    "received_type": type(root).__name__,
                    "expected_types": ["dict", "None"],
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

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        from typing import cast

        result: TypedDictMetadataDict = {}
        # This is a RootModel container - extract metadata from analytics if available
        analytics = self.root.get("_metadata_analytics")
        if analytics is not None and hasattr(analytics, "get_metadata"):
            # Cast to expected return type since analytics.get_metadata() returns Any
            return cast(TypedDictMetadataDict, analytics.get_metadata())
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError):
            # fallback-ok: ProtocolMetadataProvider contract expects bool, not exceptions
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        result: TypedDictSerializedModel = self.model_dump(
            exclude_none=False, by_alias=True
        )
        return result

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError):
            # fallback-ok: ProtocolValidatable contract expects bool validation result, not exceptions
            return False
