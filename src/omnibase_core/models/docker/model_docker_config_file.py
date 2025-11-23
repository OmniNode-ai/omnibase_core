"""Docker config file configuration model.

Pydantic model for Docker Compose config file definitions.
"""

from pydantic import BaseModel, Field


class ModelDockerConfigFile(BaseModel):
    """Docker config file configuration."""

    file: str | None = Field(default=None, description="Path to config file")
    external: bool = Field(default=False, description="External config")
    name: str | None = Field(default=None, description="Config name")
