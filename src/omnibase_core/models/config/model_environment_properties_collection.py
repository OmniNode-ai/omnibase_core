"""
Environment Properties Collection Model

Type-safe collection of environment properties with metadata support.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.types.typed_dict_property_metadata import TypedDictPropertyMetadata

from .model_property_value import ModelPropertyValue


class ModelEnvironmentPropertiesCollection(BaseModel):
    """
    Collection of environment properties with type safety.

    This model replaces dict return types to maintain strong typing
    and provide better structure for property collections.
    """

    properties: dict[str, ModelPropertyValue] = Field(
        default_factory=dict,
        description="Collection of typed property values",
    )

    property_metadata: dict[str, TypedDictPropertyMetadata] = Field(
        default_factory=dict,
        description="Metadata about each property",
    )

    def get_property_names(self) -> list[str]:
        """Get list of all property names."""
        return list(self.properties.keys())

    def get_property_count(self) -> int:
        """Get total number of properties."""
        return len(self.properties)

    def has_properties(self) -> bool:
        """Check if collection has any properties."""
        return len(self.properties) > 0

    # Note: Removed to_dict() and from_dict() methods to comply with pure Pydantic architecture
    # Use model.properties directly or ModelEnvironmentPropertiesCollection(**data) for creation


# Export the model
__all__ = [
    "ModelEnvironmentPropertiesCollection",
    "ModelPropertyValue",
]
