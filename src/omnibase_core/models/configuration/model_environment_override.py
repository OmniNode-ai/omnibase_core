from pydantic import BaseModel, Field

"""
Environment Override Model for ONEX Configuration System.

Strongly typed model for environment variable overrides.
"""


class ModelEnvironmentConfigOverride(BaseModel):
    """Typed configuration override result from environment variables."""

    default_mode: str | None = Field(
        default=None,
        description="Default mode override from environment",
    )


class ModelEnvironmentOverride(BaseModel):
    """
    Strongly typed model for environment variable overrides.

    Replaces dictionary usage in environment override handling
    with proper Pydantic validation and type safety.
    """

    registry_mode: str | None = Field(
        default=None,
        description="Override for ONEX_REGISTRY_MODE environment variable",
    )

    def to_config_dict(self) -> ModelEnvironmentConfigOverride:
        """Convert to configuration dictionary format."""
        return ModelEnvironmentConfigOverride(
            default_mode=self.registry_mode if self.registry_mode is not None else None
        )
