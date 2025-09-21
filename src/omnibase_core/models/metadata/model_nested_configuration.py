"""
Nested configuration model.

Clean, strongly-typed model for nested configuration data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field

from ...enums.enum_config_type import EnumConfigType
from ...utils.uuid_helpers import uuid_from_string


class ModelNestedConfiguration(BaseModel):
    """Model for nested configuration data."""

    # UUID-based entity references
    config_id: UUID = Field(..., description="Unique identifier for the configuration")
    config_display_name: str | None = Field(None, description="Human-readable configuration name")
    config_type: EnumConfigType = Field(
        ...,
        description="Configuration type",
    )
    settings: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Configuration settings with basic types only"
    )

    @property
    def config_name(self) -> str:
        """Get config name with fallback to UUID-based name."""
        return self.config_display_name or f"config_{str(self.config_id)[:8]}"

    @config_name.setter
    def config_name(self, value: str) -> None:
        """Set config name (for backward compatibility)."""
        self.config_display_name = value
        self.config_id = uuid_from_string(value, "config")

    @classmethod
    def create_legacy(
        cls,
        config_name: str,
        config_type: EnumConfigType,
        **kwargs,
    ) -> "ModelNestedConfiguration":
        """Create configuration with legacy name parameter for backward compatibility."""
        return cls(
            config_id=uuid_from_string(config_name, "config"),
            config_display_name=config_name,
            config_type=config_type,
            **kwargs,
        )


# Export the model
__all__ = ["ModelNestedConfiguration"]
