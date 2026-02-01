"""
Typed Configuration with Custom Properties Support.

Configuration base with custom properties support that combines the standard
configuration base with ModelCustomProperties for extensible custom fields.
"""

from __future__ import annotations

from typing import TypeVar

from .model_configuration_base import ModelConfigurationBase
from .model_custom_properties import ModelCustomProperties

T = TypeVar("T")


class ModelTypedConfiguration(
    ModelConfigurationBase[T],
    ModelCustomProperties,
):
    """
    Configuration base with custom properties support.

    Combines the standard configuration base with ModelCustomProperties
    for configurations that need extensible custom fields.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def merge_configuration(self, other: ModelTypedConfiguration[T]) -> None:
        """Merge another configuration into this one."""
        # Merge core configuration
        if other.name is not None:
            self.name = other.name
        if other.description is not None:
            self.description = other.description
        if other.version is not None:
            self.version = other.version
        if other.config_data is not None:
            self.config_data = other.config_data

        # Merge custom properties
        self.custom_strings.update(other.custom_strings)
        self.custom_numbers.update(other.custom_numbers)
        self.custom_flags.update(other.custom_flags)

        self.update_timestamp()

    def copy_configuration(self) -> ModelTypedConfiguration[T]:
        """Create a deep copy of this configuration."""
        # Use model_copy for proper Pydantic copying
        return self.model_copy(deep=True)

    def validate_and_enable(self) -> bool:
        """Validate configuration and enable if valid."""
        if self.config_data is not None:
            self.enabled = True
            self.update_timestamp()
            return True
        return False

    def disable_with_reason(self, reason: str) -> None:
        """Disable configuration and update description with reason."""
        self.enabled = False
        self.description = f"{self.description or 'Configuration'} - Disabled: {reason}"
        self.update_timestamp()

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return


# Export for use
__all__ = ["ModelTypedConfiguration"]
