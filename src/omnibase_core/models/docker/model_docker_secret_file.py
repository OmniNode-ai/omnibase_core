"""Docker secret file configuration model.

Pydantic model for Docker Compose secret file definitions.
"""

from pydantic import BaseModel, Field


class ModelDockerSecretFile(BaseModel):
    """Docker secret file configuration."""

    file: str | None = Field(default=None, description="Path to secret file")
    external: bool = Field(default=False, description="External secret")
    name: str | None = Field(default=None, description="Secret name")
