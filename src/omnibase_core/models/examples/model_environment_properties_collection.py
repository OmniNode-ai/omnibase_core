"""
Environment Properties Collection Model

Type-safe collection of environment properties with metadata support.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.types.typed_dict_property_metadata import TypedDictPropertyMetadata

from .model_property_value import ModelPropertyValue


class ModelEnvironmentPropertiesCollection(BaseModel):
    """
    Collection of environment properties with type safety.

    This model replaces dict[str, Any]return types to maintain strong typing
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
        """Get list[Any]of all property names."""
        return list(self.properties.keys())

    def get_property_count(self) -> int:
        """Get total number of properties."""
        return len(self.properties)

    def has_properties(self) -> bool:
        """Check if collection has any properties."""
        return len(self.properties) > 0

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Note: Removed to_dict() and from_dict() methods to comply with pure Pydantic architecture
    # Use model.properties directly or ModelEnvironmentPropertiesCollection(**data) for creation

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If configuration fails due to attribute or type errors
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Configuration failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        This base implementation always returns True because Pydantic's field
        validators and type checking already enforce validation rules at
        construction time. This method exists to satisfy the ProtocolValidatable
        protocol interface.

        Returns:
            True: Instance is valid (validation was enforced at construction)

        Note:
            Subclasses may override to add runtime validation beyond what
            Pydantic validators provide at construction time.
        """
        return True


__all__ = [
    "ModelEnvironmentPropertiesCollection",
    "ModelPropertyValue",
]
