"""
Service container model.
"""

from pydantic import BaseModel, Field


class ModelServiceContainer(BaseModel):
    """Service container configuration."""

    image: str = Field(default=..., description="Container image")
    env: dict[str, str] | None = Field(
        default=None, description="Environment variables"
    )
    ports: list[str] | None = Field(default=None, description="Exposed ports")
    volumes: list[str] | None = Field(default=None, description="Volume mounts")
    options: str | None = Field(default=None, description="Container options")
    credentials: dict[str, str] | None = Field(
        default=None,
        description="Registry credentials",
    )
