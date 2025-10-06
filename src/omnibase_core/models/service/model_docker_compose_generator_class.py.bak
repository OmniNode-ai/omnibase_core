"""Docker Compose Generator Model.

Generator for Docker Compose configurations from ONEX service schemas.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omnibase_core.models.configuration.model_docker_build_config import (
        ModelDockerBuildConfig,
    )
    from omnibase_core.models.configuration.model_docker_deploy_config import (
        ModelDockerDeployConfig,
    )
    from omnibase_core.models.configuration.model_docker_healthcheck_config import (
        ModelDockerHealthcheckConfig,
    )
    from omnibase_core.models.configuration.model_docker_network_config import (
        ModelDockerNetworkConfig,
    )
    from omnibase_core.models.configuration.model_docker_volume_config import (
        ModelDockerVolumeConfig,
    )
    from omnibase_core.models.configuration.model_node_service_config import (
        ModelNodeServiceConfig,
    )
    from omnibase_core.models.service.model_compose_service_definition import (
        ModelComposeServiceDefinition,
    )
    from omnibase_core.models.service.model_docker_compose_config import (
        ModelDockerComposeConfig,
    )
    from omnibase_core.models.service.model_service_dependency import (
        ModelServiceDependency,
    )

from omnibase_core.errors import ModelOnexError
from omnibase_core.errors.error_codes import ModelCoreErrorCode

# Import with fallback handling
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

try:
    import json

    HAS_JSON = True
except ImportError:
    HAS_JSON = False
    json = None


class ModelDockerComposeGenerator:
    """Generator for Docker Compose configurations from ONEX service schemas."""

    def __init__(
        self,
        services: "list[ModelNodeServiceConfig]",
        project_name: str = "onex-services",
        include_infrastructure: bool = True,
    ):
        """
        Initialize compose generator with service configurations.

        Args:
            services: List of ONEX service configurations
            project_name: Docker Compose project name
            include_infrastructure: Whether to include infrastructure services
        """
        self.services = services
        self.project_name = project_name
        self.include_infrastructure = include_infrastructure
        self.service_definitions: dict[str, "ModelComposeServiceDefinition"] = {}
        self.networks: dict[str, "ModelDockerNetworkConfig"] = {}
        self.volumes: dict[str, "ModelDockerVolumeConfig"] = {}
