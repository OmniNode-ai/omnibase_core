"""Compose Service Definition Model.

Complete service definition for Docker Compose.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.docker.model_docker_build_config import (
        ModelDockerBuildConfig,
    )
    from omnibase_core.models.docker.model_docker_deploy_config import (
        ModelDockerDeployConfig,
    )
    from omnibase_core.models.docker.model_docker_healthcheck_config import (
        ModelDockerHealthcheckConfig,
    )


@dataclass
class ModelComposeServiceDefinition:
    """Complete service definition for Docker Compose."""

    name: str
    image: str | None = None
    build: "ModelDockerBuildConfig | None" = None
    command: str | list[str] | None = None
    environment: dict[str, str] | None = None
    ports: list[str] | None = None
    volumes: list[str] | None = None
    depends_on: dict[str, dict[str, str]] | None = None
    healthcheck: "ModelDockerHealthcheckConfig | None" = None
    restart: str = "unless-stopped"
    networks: list[str] | None = None
    labels: dict[str, str] | None = None
    deploy: "ModelDockerDeployConfig | None" = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.environment is None:
            self.environment = {}
        if self.ports is None:
            self.ports = []
        if self.volumes is None:
            self.volumes = []
        if self.depends_on is None:
            self.depends_on = {}
        if self.networks is None:
            self.networks = []
        if self.labels is None:
            self.labels = {}
