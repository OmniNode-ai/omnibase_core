"""
Environment Properties Model

Type-safe custom environment properties with access methods.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar, cast, get_origin

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Type variable for generic property handling
T = TypeVar("T")
from omnibase_core.types.typed_dict_property_metadata import TypedDictPropertyMetadata

from .model_environment_properties_collection import (
    ModelEnvironmentPropertiesCollection,
)
from .model_property_value import ModelPropertyValue


class ModelEnvironmentProperties(BaseModel):
    """
    Type-safe custom environment properties.

    This model provides structured storage for custom environment properties
    with type safety and helper methods for property access.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    properties: dict[str, ModelPropertyValue] = Field(
        default_factory=dict,
        description="Custom property values",
    )

    property_metadata: dict[str, TypedDictPropertyMetadata] = Field(
        default_factory=dict,
        description="Metadata about each property (description, source, etc.)",
    )

    def get_typed_value(self, key: str, expected_type: type[T], default: T) -> T:
        """Get property value with specific type checking using generic type inference."""
        prop_value = self.properties.get(key)
        if prop_value is None:
            return default

        try:
            # Use ModelPropertyValue's type-safe accessors based on expected type
            # Use 'is' for type identity comparisons (PEP 8 compliant)
            if expected_type is str:
                return cast(T, prop_value.as_string())
            if expected_type is int:
                return cast(T, prop_value.as_int())
            if expected_type is float:
                return cast(T, prop_value.as_float())
            if expected_type is bool:
                return cast(T, prop_value.as_bool())
            # Check for list types using get_origin for generic type aliases
            if get_origin(expected_type) is list:
                # Handle list types
                if hasattr(prop_value, "value") and isinstance(prop_value.value, list):
                    return cast(T, [str(item) for item in prop_value.value])
                # Try string conversion for comma-separated values
                str_val = prop_value.as_string()
                return cast(
                    T,
                    [item.strip() for item in str_val.split(",") if item.strip()],
                )
            if hasattr(prop_value, "value") and isinstance(
                prop_value.value,
                expected_type,
            ):
                return prop_value.value
        except (AttributeError, ValueError):
            pass

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
            # Try parsing from string
            str_val = prop_value.as_string()
            return datetime.fromisoformat(str_val)
        except (AttributeError, ValueError):
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
        self,
        prefix: str,
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Returns True for well-constructed instances. Override in subclasses
        for custom validation logic.
        """
        # Basic validation - Pydantic handles field constraints
        # Override in specific models for custom validation
        return True


__all__ = ["ModelEnvironmentProperties"]
