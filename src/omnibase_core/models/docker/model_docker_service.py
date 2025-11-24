"""Docker Compose service definition model.

Pydantic model for Docker Compose service configurations.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.docker.model_docker_build_config import ModelDockerBuildConfig
from omnibase_core.models.docker.model_docker_deploy_config import (
    ModelDockerDeployConfig,
)
from omnibase_core.models.docker.model_docker_healthcheck_config import (
    ModelDockerHealthcheckConfig,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDockerService(BaseModel):
    """Docker Compose service definition (Pydantic version)."""

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version",
    )
    name: str = Field(description="Service name")
    image: str | None = Field(default=None, description="Docker image")
    build: ModelDockerBuildConfig | None = Field(
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
    healthcheck: ModelDockerHealthcheckConfig | None = Field(
        default=None,
        description="Health check configuration",
    )
    restart: str = Field(default="unless-stopped", description="Restart policy")
    networks: list[str] | None = Field(default=None, description="Networks to join")
    labels: dict[str, str] | None = Field(
        default=None,
        description="Container labels",
    )
    deploy: ModelDockerDeployConfig | None = Field(
        default=None,
        description="Deploy configuration",
    )
