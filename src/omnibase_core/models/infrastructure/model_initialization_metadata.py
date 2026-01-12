"""
Initialization Metadata Model.

Strongly-typed model for node initialization metadata, replacing dict[str, Any]
in ModelNodeState.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelInitializationMetadata(BaseModel):
    """
    Typed model for node initialization metadata.

    Replaces dict[str, Any] initialization_metadata in ModelNodeState.
    Provides structured storage for common initialization properties.
    """

    # Timing information
    initialized_at: datetime | None = Field(
        default=None,
        description="When initialization completed",
    )

    # Source information
    source: str = Field(
        default="",
        description="Source of initialization (e.g., 'container', 'manual')",
    )

    # Configuration loaded
    config_loaded: bool = Field(
        default=False,
        description="Whether configuration was loaded successfully",
    )

    # Dependencies resolved
    dependencies_resolved: bool = Field(
        default=False,
        description="Whether all dependencies were resolved",
    )

    # Additional typed properties
    properties: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional initialization properties",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ModelInitializationMetadata:
        """Create from a plain dictionary."""
        # Extract known fields
        initialized_at = data.get("initialized_at")
        source = data.get("source", "")
        config_loaded = data.get("config_loaded", False)
        dependencies_resolved = data.get("dependencies_resolved", False)

        # Convert remaining to properties
        known_keys = {
            "initialized_at",
            "source",
            "config_loaded",
            "dependencies_resolved",
        }
        properties = {
            key: ModelSchemaValue.from_value(value)
            for key, value in data.items()
            if key not in known_keys
        }

        return cls(
            initialized_at=(
                initialized_at if isinstance(initialized_at, datetime) else None
            ),
            source=str(source) if source else "",
            config_loaded=bool(config_loaded),
            dependencies_resolved=bool(dependencies_resolved),
            properties=properties,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to plain dictionary."""
        result: dict[str, object] = {
            "source": self.source,
            "config_loaded": self.config_loaded,
            "dependencies_resolved": self.dependencies_resolved,
        }
        if self.initialized_at:
            result["initialized_at"] = self.initialized_at
        for key, value in self.properties.items():
            result[key] = value.to_value()
        return result

    def get_property(self, key: str, default: object = None) -> object:
        """Get an additional property by key."""
        schema_value = self.properties.get(key)
        if schema_value is None:
            return default
        return schema_value.to_value()

    def set_property(self, key: str, value: object) -> None:
        """Set an additional property."""
        self.properties[key] = ModelSchemaValue.from_value(value)


__all__ = ["ModelInitializationMetadata"]
