"""
Environment Override Model for ONEX Configuration System.

Strongly typed model for environment variable overrides.
"""

from pydantic import BaseModel, ConfigDict, Field

from .model_environment_config_override import ModelEnvironmentConfigOverride

# Re-export from split module
__all__ = ["ModelEnvironmentOverride", "ModelEnvironmentConfigOverride"]


class ModelEnvironmentOverride(BaseModel):
    """
    Strongly typed model for environment variable overrides.

    Replaces dictionary usage in environment override handling
    with proper Pydantic validation and type safety.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    registry_mode: str | None = Field(
        default=None,
        description="Override for ONEX_REGISTRY_MODE environment variable",
    )

    def to_config_dict(self) -> ModelEnvironmentConfigOverride:
        """Convert to configuration dictionary format."""
        return ModelEnvironmentConfigOverride(
            default_mode=self.registry_mode if self.registry_mode is not None else None
        )
