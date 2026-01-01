"""
Environment Config Override Model for ONEX Configuration System.

Strongly typed model for environment variable configuration override results.
"""

from pydantic import BaseModel, Field


class ModelEnvironmentConfigOverride(BaseModel):
    """Typed configuration override result from environment variables."""

    default_mode: str | None = Field(
        default=None,
        description="Default mode override from environment",
    )
