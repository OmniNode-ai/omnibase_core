"""
Environment Override Model for ONEX Configuration System.

Strongly typed model for environment variable overrides.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelEnvironmentOverride(BaseModel):
    """
    Strongly typed model for environment variable overrides.

    Replaces dictionary usage in environment override handling
    with proper Pydantic validation and type safety.
    """

    registry_mode: Optional[str] = Field(
        default=None, description="Override for ONEX_REGISTRY_MODE environment variable"
    )

    def to_config_dict(self) -> dict:
        """Convert to configuration dictionary format."""
        overrides = {}
        if self.registry_mode is not None:
            overrides["default_mode"] = self.registry_mode
        return overrides
