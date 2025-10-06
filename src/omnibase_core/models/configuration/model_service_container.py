from pydantic import Field

"""
Service container model.
"""

from pydantic import BaseModel, Field


class ModelServiceContainer(BaseModel):
    """Service container configuration."""

    image: str = Field(..., description="Container image")
    env: dict[str, str] | None = Field(None, description="Environment variables")
    ports: list[str] | None = Field(None, description="Exposed ports")
    volumes: list[str] | None = Field(None, description="Volume mounts")
    options: str | None = Field(None, description="Container options")
    credentials: dict[str, str] | None = Field(
        None,
        description="Registry credentials",
    )
