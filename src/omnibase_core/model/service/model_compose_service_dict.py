"""
Model for Docker Compose service dictionary representation.
"""

from pydantic import BaseModel, Field


class ModelComposeServiceDict(BaseModel):
    """Dictionary representation of a compose service for YAML serialization."""

    image: str | None = Field(default=None, description="Docker image")
    build: dict[str, str] | None = Field(
        default=None,
        description="Build configuration",
    )
    command: str | list[str] | None = Field(
        default=None,
        description="Command to run",
    )
    environment: dict[str, str] | None = Field(
        default=None,
        description="Environment variables",
    )
    ports: list[str] | None = Field(default=None, description="Port mappings")
    volumes: list[str] | None = Field(default=None, description="Volume mounts")
    depends_on: dict[str, dict[str, str]] | None = Field(
        default=None,
        description="Service dependencies",
    )
    healthcheck: dict[str, str | int | list[str]] | None = Field(
        default=None,
        description="Health check config",
    )
    restart: str | None = Field(default=None, description="Restart policy")
    networks: list[str] | None = Field(default=None, description="Networks to join")
    labels: dict[str, str] | None = Field(
        default=None,
        description="Container labels",
    )
    deploy: dict[str, dict[str, str | int | dict[str, str]]] | None = Field(
        default=None,
        description="Deploy config",
    )
