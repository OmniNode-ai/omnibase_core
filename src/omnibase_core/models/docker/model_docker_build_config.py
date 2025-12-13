"""
Model for Docker build configuration.
"""

from pydantic import BaseModel, Field


class ModelDockerBuildConfig(BaseModel):
    """Docker build configuration for compose services."""

    context: str = Field(default=".", description="Build context path")
    dockerfile: str = Field(default="Dockerfile", description="Path to Dockerfile")
    args: dict[str, str] | None = Field(default=None, description="Build arguments")
    target: str | None = Field(default=None, description="Build target stage")
    cache_from: list[str] | None = Field(
        default=None,
        description="Images to use as cache sources",
    )
    labels: dict[str, str] | None = Field(default=None, description="Build labels")
