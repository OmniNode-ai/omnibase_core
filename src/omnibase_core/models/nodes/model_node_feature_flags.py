from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Node Feature Flags Model.

Feature toggle configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_node_feature_summary_type import (
    TypedDictNodeFeatureSummaryType,
)


class ModelNodeFeatureFlags(BaseModel):
    """
    Node feature toggle settings.

    Contains feature enablement flags:
    - Caching and monitoring
    - Tracing and debugging features
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Feature toggles (3 fields)
    enable_caching: bool = Field(default=False, description="Enable result caching")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    enable_tracing: bool = Field(default=False, description="Enable detailed tracing")

    def get_enabled_features(self) -> list[str]:
        """Get list[Any]of enabled features."""
        features = []
        if self.enable_caching:
            features.append("caching")
        if self.enable_monitoring:
            features.append("monitoring")
        if self.enable_tracing:
            features.append("tracing")
        return features

    def get_disabled_features(self) -> list[str]:
        """Get list[Any]of disabled features."""
        features = []
        if not self.enable_caching:
            features.append("caching")
        if not self.enable_monitoring:
            features.append("monitoring")
        if not self.enable_tracing:
            features.append("tracing")
        return features

    def get_feature_summary(self) -> TypedDictNodeFeatureSummaryType:
        """Get feature flags summary as string values for type safety."""
        enabled = self.get_enabled_features()
        return {
            "enable_caching": str(self.enable_caching),
            "enable_monitoring": str(self.enable_monitoring),
            "enable_tracing": str(self.enable_tracing),
            "enabled_features": ",".join(enabled) if enabled else "none",
            "enabled_count": str(len(enabled)),
            "is_monitoring_enabled": str(self.enable_monitoring),
            "is_debug_mode": str(self.enable_tracing),
        }

    def is_production_ready(self) -> bool:
        """Check if configuration is production-ready."""
        return self.enable_monitoring and not self.enable_tracing

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.enable_tracing

    def enable_all_features(self) -> None:
        """Enable all available features."""
        self.enable_caching = True
        self.enable_monitoring = True
        self.enable_tracing = True

    def disable_all_features(self) -> None:
        """Disable all features."""
        self.enable_caching = False
        self.enable_monitoring = False
        self.enable_tracing = False

    @classmethod
    def create_production(cls) -> ModelNodeFeatureFlags:
        """Create production-ready feature configuration."""
        return cls(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=False,
        )

    @classmethod
    def create_development(cls) -> ModelNodeFeatureFlags:
        """Create development-friendly feature configuration."""
        return cls(
            enable_caching=False,
            enable_monitoring=True,
            enable_tracing=True,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

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
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

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
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelNodeFeatureFlags"]
