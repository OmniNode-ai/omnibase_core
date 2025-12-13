"""
Model for Docker volume configuration.
"""

from pydantic import BaseModel, Field


class ModelDockerVolumeConfig(BaseModel):
    """Docker volume configuration for compose."""

    driver: str | None = Field(default=None, description="Volume driver")
    driver_opts: dict[str, str] | None = Field(
        default=None,
        description="Driver options",
    )
    external: bool | None = Field(default=False, description="External volume")
    name: str | None = Field(default=None, description="Volume name")
