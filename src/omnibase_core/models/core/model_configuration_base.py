"""
Generic Configuration Base Class.

Standardizes common patterns found across Config domain models,
eliminating field duplication and providing consistent configuration interfaces.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import Result
from omnibase_core.models.metadata.model_semver import ModelSemVer

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
    ) -> Result[ModelSchemaValue, str]:
        """Get configuration value by key from config_data."""
        if self.config_data and hasattr(self.config_data, key):
            value = getattr(self.config_data, key)
            if isinstance(value, (str, int, bool, float)):
                return Result.ok(ModelSchemaValue.from_value(value))
            if default is not None:
                return Result.ok(default)
            return Result.err(
                f"Config value '{key}' has unsupported type: {type(value)}"
            )
        if default is not None:
            return Result.ok(default)
        return Result.err(f"Config key '{key}' not found in config_data")

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
    def validate_configuration(self) -> ModelConfigurationBase[T]:
        """Override in subclasses for custom validation."""
        return self

    @classmethod
    def create_empty(cls, name: str) -> ModelConfigurationBase[T]:
        """Create an empty configuration with a name."""
        return cls(name=name, description=f"Empty {name} configuration")

    @classmethod
    def create_with_data(cls, name: str, config_data: T) -> ModelConfigurationBase[T]:
        """Create configuration with typed data."""
        return cls(name=name, config_data=config_data)

    @classmethod
    def create_disabled(cls, name: str) -> ModelConfigurationBase[T]:
        """Create a disabled configuration."""
        return cls(
            name=name,
            enabled=False,
            description=f"Disabled {name} configuration",
        )


# Export for use
__all__ = ["ModelConfigurationBase"]
