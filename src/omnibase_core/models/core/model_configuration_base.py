"""
Generic Configuration Base Class.

Standardizes common patterns found across Config domain models,
eliminating field duplication and providing consistent configuration interfaces.
"""

from datetime import UTC, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field, model_validator

from ..metadata.model_semver import ModelSemVer
from .model_custom_properties import ModelCustomProperties

T = TypeVar("T")


class ModelConfigurationBase(BaseModel, Generic[T]):
    """
    Base class for all configuration models with common patterns.

    Provides standardized fields and methods found across configuration models:
    - Common metadata fields (name, description, version)
    - Lifecycle fields (enabled, timestamps)
    - Generic typed configuration data
    - Common utility methods
    """

    # Core metadata
    name: Optional[str] = Field(default=None, description="Configuration name")
    description: Optional[str] = Field(
        default=None, description="Configuration description"
    )
    version: Optional[ModelSemVer] = Field(
        default=None, description="Configuration version"
    )

    # Lifecycle control
    enabled: bool = Field(default=True, description="Whether configuration is enabled")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Generic configuration data
    config_data: Optional[T] = Field(
        default=None, description="Typed configuration data"
    )

    def update_timestamp(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(UTC)

    def get_config_value(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get configuration value by key from config_data."""
        if self.config_data and hasattr(self.config_data, key):
            value = getattr(self.config_data, key)
            return value if isinstance(value, (str, int, bool, float)) else default
        return default

    def is_enabled(self) -> bool:
        """Check if configuration is enabled."""
        return self.enabled

    def is_valid(self) -> bool:
        """Check if configuration is valid (enabled and has required data)."""
        return self.enabled and self.config_data is not None

    def get_display_name(self) -> str:
        """Get display name, falling back to 'Unnamed Configuration'."""
        return self.name or "Unnamed Configuration"

    def get_version_or_default(self) -> str:
        """Get version string, falling back to '1.0.0'."""
        return str(self.version) if self.version else "1.0.0"

    @model_validator(mode="after")
    def validate_configuration(self) -> "ModelConfigurationBase[T]":
        """Override in subclasses for custom validation."""
        return self

    @classmethod
    def create_empty(cls, name: str) -> "ModelConfigurationBase[T]":
        """Create an empty configuration with a name."""
        return cls(name=name, description=f"Empty {name} configuration")

    @classmethod
    def create_with_data(cls, name: str, config_data: T) -> "ModelConfigurationBase[T]":
        """Create configuration with typed data."""
        return cls(name=name, config_data=config_data)

    @classmethod
    def create_disabled(cls, name: str) -> "ModelConfigurationBase[T]":
        """Create a disabled configuration."""
        return cls(
            name=name, enabled=False, description=f"Disabled {name} configuration"
        )


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
__all__ = [
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
]
