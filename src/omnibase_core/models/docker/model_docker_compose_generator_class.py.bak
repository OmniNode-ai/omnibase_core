"""Docker Compose Generator Model.

Generator for Docker Compose configurations from ONEX service schemas.
"""

from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omnibase_core.models.docker.model_compose_service_definition import (
        ModelComposeServiceDefinition,
    )
    from omnibase_core.models.docker.model_docker_build_config import (
        ModelDockerBuildConfig,
    )
    from omnibase_core.models.docker.model_docker_compose_config import (
        ModelDockerComposeConfig,
    )
    from omnibase_core.models.docker.model_docker_deploy_config import (
        ModelDockerDeployConfig,
    )
    from omnibase_core.models.docker.model_docker_healthcheck_config import (
        ModelDockerHealthcheckConfig,
    )
    from omnibase_core.models.docker.model_docker_network_config import (
        ModelDockerNetworkConfig,
    )
    from omnibase_core.models.docker.model_docker_volume_config import (
        ModelDockerVolumeConfig,
    )
    from omnibase_core.models.service.model_node_service_config import (
        ModelNodeServiceConfig,
    )
    from omnibase_core.models.service.model_service_dependency import (
        ModelServiceDependency,
    )

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

# Import with fallback handling
yaml_module: ModuleType | None
try:
    import yaml

    HAS_YAML = True
    yaml_module = yaml
except ImportError:
    HAS_YAML = False
    yaml_module = None

json_module: ModuleType | None
try:
    import json

    HAS_JSON = True
    json_module = json
except ImportError:
    HAS_JSON = False
    json_module = None


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
        self.service_definitions: dict[str, ModelComposeServiceDefinition] = {}
        self.networks: dict[str, ModelDockerNetworkConfig] = {}
        self.volumes: dict[str, ModelDockerVolumeConfig] = {}
