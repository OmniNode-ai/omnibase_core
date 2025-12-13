"""
Model for Docker network configuration.
"""

from pydantic import BaseModel, Field


class ModelDockerNetworkConfig(BaseModel):
    """Docker network configuration for compose."""

    driver: str = Field(default="bridge", description="Network driver")
    driver_opts: dict[str, str] | None = Field(
        default=None,
        description="Driver options",
    )
    external: bool | None = Field(default=False, description="External network")
    name: str | None = Field(default=None, description="Network name")
