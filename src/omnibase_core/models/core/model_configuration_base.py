"""
Generic Configuration Base Class.

Standardizes common patterns found across Config domain models,
eliminating field duplication and providing consistent configuration interfaces.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from omnibase_core.core.type_constraints import (
    Configurable,
    Nameable,
    Serializable,
    Validatable,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import ModelResult
from omnibase_core.models.metadata.model_semver import ModelSemVer

# Type variable for configuration data with proper constraints
T = TypeVar("T", bound=Serializable)


class ModelConfigurationBase(BaseModel, Generic[T]):
    """
    Base class for all configuration models with common patterns.

    Provides standardized fields and methods found across configuration models:
    - Common metadata fields (name, description, version)
    - Lifecycle fields (enabled, timestamps)
    - Generic typed configuration data
    - Common utility methods

    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    # Core metadata
    name: str | None = Field(default=None, description="Configuration name")
    description: str | None = Field(
        default=None,
        description="Configuration description",
    )
    version: ModelSemVer | None = Field(
        default=None,
        description="Configuration version",
    )

    # Lifecycle control
    enabled: bool = Field(default=True, description="Whether configuration is enabled")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Generic configuration data
    config_data: T | None = Field(default=None, description="Typed configuration data")

    def update_timestamp(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(UTC)

    def get_config_value(
        self,
        key: str,
        default: ModelSchemaValue | None = None,
    ) -> ModelResult[ModelSchemaValue, str]:
        """Get configuration value by key from config_data."""
        if self.config_data and hasattr(self.config_data, key):
            value = getattr(self.config_data, key)
            if isinstance(value, (str, int, bool, float)):
                return ModelResult.ok(ModelSchemaValue.from_value(value))
            if default is not None:
                return ModelResult.ok(default)
            return ModelResult.err(
                f"Config value '{key}' has unsupported type: {type(value)}"
            )
        if default is not None:
            return ModelResult.ok(default)
        return ModelResult.err(f"Config key '{key}' not found in config_data")

    def is_enabled(self) -> bool:
        """Check if configuration is enabled."""
        return self.enabled

    def validate_instance(self) -> bool:
        """Check if configuration is valid (enabled and has required data) (Validatable protocol)."""
        try:
            # Basic validation - configuration enabled and has data
            base_valid = self.enabled and self.config_data is not None
            # Additional protocol-specific validation
            if self.name is not None and len(self.name.strip()) == 0:
                return False
            return base_valid
        except Exception:
            return False

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
    def create_empty(cls, name: str) -> ModelConfigurationBase[Any]:
        """Create an empty configuration with a name."""
        return cls(name=name, description=f"Empty {name} configuration")

    @classmethod
    def create_with_data(cls, name: str, config_data: T) -> ModelConfigurationBase[T]:
        """Create configuration with typed data."""
        return cls(name=name, config_data=config_data)

    @classmethod
    def create_disabled(cls, name: str) -> ModelConfigurationBase[Any]:
        """Create a disabled configuration."""
        return cls(
            name=name,
            enabled=False,
            description=f"Disabled {name} configuration",
        )

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize configuration to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                elif key == "config_data":
                    self.config_data = value
            self.update_timestamp()
            return True
        except Exception:
            return False

    def get_name(self) -> str:
        """Get configuration name (Nameable protocol)."""
        return self.get_display_name()

    def set_name(self, name: str) -> None:
        """Set configuration name (Nameable protocol)."""
        self.name = name
        self.update_timestamp()


# Export for use
__all__ = ["ModelConfigurationBase"]
