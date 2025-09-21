"""
Environment Properties Model

Type-safe custom environment properties with access methods.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .model_environment_properties_collection import (
    ModelEnvironmentPropertiesCollection,
    TypedDictPropertyMetadata,
)
from .model_property_value import ModelPropertyValue


class ModelEnvironmentProperties(BaseModel):
    """
    Type-safe custom environment properties.

    This model provides structured storage for custom environment properties
    with type safety and helper methods for property access.
    """

    properties: dict[str, ModelPropertyValue] = Field(
        default_factory=dict,
        description="Custom property values",
    )

    property_metadata: dict[str, TypedDictPropertyMetadata] = Field(
        default_factory=dict,
        description="Metadata about each property (description, source, etc.)",
    )

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value."""
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default
        try:
            return prop_value.as_string()
        except (ValueError, AttributeError):
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value."""
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default
        try:
            return prop_value.as_int()
        except (ValueError, AttributeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float property value."""
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default
        try:
            return prop_value.as_float()
        except (ValueError, AttributeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value."""
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default
        try:
            return prop_value.as_bool()
        except (ValueError, AttributeError):
            return default

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get list property value."""
        if default is None:
            default = []
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default
        try:
            # ModelPropertyValue doesn't have as_list, use the value directly
            if hasattr(prop_value, "value") and isinstance(prop_value.value, list):
                return [str(item) for item in prop_value.value]
            else:
                # Try string conversion for comma-separated values
                str_val = prop_value.as_string()
                return [item.strip() for item in str_val.split(",") if item.strip()]
        except (ValueError, AttributeError):
            return default

    def get_datetime(
        self,
        key: str,
        default: datetime | None = None,
    ) -> datetime | None:
        """Get datetime property value."""
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default
        try:
            # Access the datetime value directly
            if hasattr(prop_value, "value") and isinstance(prop_value.value, datetime):
                return prop_value.value
            else:
                # Try parsing from string
                str_val = prop_value.as_string()
                return datetime.fromisoformat(str_val)
        except (ValueError, AttributeError):
            return default

    def set_property(
        self,
        key: str,
        value: ModelPropertyValue,
        description: str | None = None,
        source: str | None = None,
    ) -> None:
        """Set a property with optional metadata."""
        self.properties[key] = value

        if description or source:
            metadata = self.property_metadata.get(key, {})
            if description:
                metadata["description"] = description
            if source:
                metadata["source"] = source
            self.property_metadata[key] = metadata

    def remove_property(self, key: str) -> None:
        """Remove a property and its metadata."""
        self.properties.pop(key, None)
        self.property_metadata.pop(key, None)

    def has_property(self, key: str) -> bool:
        """Check if a property exists."""
        return key in self.properties

    def get_property_description(self, key: str) -> str | None:
        """Get property description from metadata."""
        metadata = self.property_metadata.get(key, {})
        return metadata.get("description")

    def get_property_source(self, key: str) -> str | None:
        """Get property source from metadata."""
        metadata = self.property_metadata.get(key, {})
        return metadata.get("source")

    def get_all_properties(
        self,
    ) -> ModelEnvironmentPropertiesCollection:
        """Get all properties as a strongly-typed collection."""
        return ModelEnvironmentPropertiesCollection(
            properties=self.properties.copy(),
            property_metadata=self.property_metadata.copy(),
        )

    def get_properties_by_prefix(
        self, prefix: str
    ) -> ModelEnvironmentPropertiesCollection:
        """Get all properties with keys starting with a prefix as a strongly-typed collection."""
        filtered_properties = {
            key: value
            for key, value in self.properties.items()
            if key.startswith(prefix)
        }
        filtered_metadata = {
            key: metadata
            for key, metadata in self.property_metadata.items()
            if key.startswith(prefix)
        }
        return ModelEnvironmentPropertiesCollection(
            properties=filtered_properties,
            property_metadata=filtered_metadata,
        )

    def merge_properties(self, other: ModelEnvironmentProperties) -> None:
        """Merge properties from another instance."""
        self.properties.update(other.properties)
        self.property_metadata.update(other.property_metadata)

    def to_environment_variables(self, prefix: str = "ONEX_CUSTOM_") -> dict[str, str]:
        """Convert properties to environment variables with prefix."""
        env_vars = {}
        for key, prop_value in self.properties.items():
            env_key = f"{prefix}{key.upper()}"
            # Use the actual value from ModelPropertyValue
            if hasattr(prop_value, "value"):
                actual_value = prop_value.value
                if isinstance(actual_value, list):
                    env_vars[env_key] = ",".join(str(item) for item in actual_value)
                elif isinstance(actual_value, datetime):
                    env_vars[env_key] = actual_value.isoformat()
                else:
                    env_vars[env_key] = str(actual_value)
            else:
                env_vars[env_key] = str(prop_value)
        return env_vars

    @classmethod
    def create_empty(cls) -> ModelEnvironmentProperties:
        """Create empty properties instance."""
        return cls()


# Export the model
__all__ = ["ModelEnvironmentProperties"]
