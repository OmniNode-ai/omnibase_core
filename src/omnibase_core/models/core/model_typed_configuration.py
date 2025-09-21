"""
Typed Configuration with Custom Properties Support.

Configuration base with custom properties support that combines the standard
configuration base with ModelCustomProperties for extensible custom fields.
"""

from typing import TypeVar

from .model_configuration_base import ModelConfigurationBase
from .model_custom_properties import ModelCustomProperties

T = TypeVar("T")


class ModelTypedConfiguration(ModelConfigurationBase[T], ModelCustomProperties):
    """
    Configuration base with custom properties support.

    Combines the standard configuration base with ModelCustomProperties
    for configurations that need extensible custom fields.
    """

    def merge_configuration(self, other: "ModelTypedConfiguration[T]") -> None:
        """Merge another configuration into this one."""
        # Merge core configuration
        if other.name:
            self.name = other.name
        if other.description:
            self.description = other.description
        if other.version:
            self.version = other.version
        if other.config_data:
            self.config_data = other.config_data

        # Merge custom properties
        self.custom_strings.update(other.custom_strings)
        self.custom_numbers.update(other.custom_numbers)
        self.custom_flags.update(other.custom_flags)

        self.update_timestamp()

    def copy_configuration(self) -> "ModelTypedConfiguration[T]":
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


# Export for use
__all__ = ["ModelTypedConfiguration"]
