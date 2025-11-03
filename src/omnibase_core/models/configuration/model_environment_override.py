from typing import Any

from pydantic import Field

"""
Environment Override Model for ONEX Configuration System.

Strongly typed model for environment variable overrides.
"""

from pydantic import BaseModel


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

    def to_config_dict(self) -> dict[str, Any]:
        """Convert to configuration dictionary format."""
        overrides = {}
        if self.registry_mode is not None:
            overrides["default_mode"] = self.registry_mode
        return overrides
