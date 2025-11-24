"""Docker deployment and Docker Compose models.

This package contains all models related to Docker deployment,
Docker Compose configuration, and container orchestration.
"""

# Docker Compose service models
from omnibase_core.models.docker.model_compose_service_definition import (
    ModelComposeServiceDefinition,
)
from omnibase_core.models.docker.model_compose_service_dict import (
    ModelComposeServiceDict,
)

# Docker build configuration
from omnibase_core.models.docker.model_docker_build_config import ModelDockerBuildConfig

# Docker command models
from omnibase_core.models.docker.model_docker_command import ModelDockerCommand

# Docker Compose configuration
from omnibase_core.models.docker.model_docker_compose_config import (
    ModelDockerComposeConfig,
)

# Docker Compose generator
from omnibase_core.models.docker.model_docker_compose_generator import (
    ModelDockerComposeGenerator,
)
from omnibase_core.models.docker.model_docker_compose_generator_class import (
    ModelDockerComposeGenerator as ModelDockerComposeGeneratorClass,
)

# Docker Compose manifest
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest,
)

# Docker Compose config and secret files
from omnibase_core.models.docker.model_docker_config_file import ModelDockerConfigFile

# Docker deployment configuration
from omnibase_core.models.docker.model_docker_deploy_config import (
    ModelDockerDeployConfig,
    ModelDockerResourceLimits,
    ModelDockerResourceReservations,
    ModelDockerResources,
)
from omnibase_core.models.docker.model_docker_deploy_config_class import (
    ModelDockerDeployConfig as ModelDockerDeployConfigClass,
)

# Docker healthcheck
from omnibase_core.models.docker.model_docker_healthcheck_config import (
    ModelDockerHealthcheckConfig,
)
from omnibase_core.models.docker.model_docker_healthcheck_test import (
    ModelDockerHealthcheckTest,
)

# Docker network configuration
from omnibase_core.models.docker.model_docker_network_config import (
    ModelDockerNetworkConfig,
)

# Docker placement constraints
from omnibase_core.models.docker.model_docker_placement_constraints import (
    ModelDockerPlacementConstraints,
)

# Docker restart policy
from omnibase_core.models.docker.model_docker_restart_policy import (
    ModelDockerRestartPolicy,
)
from omnibase_core.models.docker.model_docker_secret_file import ModelDockerSecretFile

# Docker Compose service
from omnibase_core.models.docker.model_docker_service import ModelDockerService

# Docker template generator
from omnibase_core.models.docker.model_docker_template_generator import (
    ModelDockerTemplateGenerator,
)

# Docker volume configuration
from omnibase_core.models.docker.model_docker_volume_config import (
    ModelDockerVolumeConfig,
)

__all__ = [
    # Compose service models
    "ModelComposeServiceDefinition",
    "ModelComposeServiceDict",
    # Build configuration
    "ModelDockerBuildConfig",
    # Command models
    "ModelDockerCommand",
    # Compose configuration
    "ModelDockerComposeConfig",
    # Compose generator
    "ModelDockerComposeGenerator",
    "ModelDockerComposeGeneratorClass",
    # Compose manifest
    "ModelDockerComposeManifest",
    "ModelDockerConfigFile",
    "ModelDockerSecretFile",
    "ModelDockerService",
    # Deploy configuration
    "ModelDockerDeployConfig",
    "ModelDockerDeployConfigClass",
    "ModelDockerResourceLimits",
    "ModelDockerResourceReservations",
    "ModelDockerResources",
    # Healthcheck
    "ModelDockerHealthcheckConfig",
    "ModelDockerHealthcheckTest",
    # Network configuration
    "ModelDockerNetworkConfig",
    # Placement constraints
    "ModelDockerPlacementConstraints",
    # Restart policy
    "ModelDockerRestartPolicy",
    # Template generator
    "ModelDockerTemplateGenerator",
    # Volume configuration
    "ModelDockerVolumeConfig",
]

# Rebuild models after all imports to resolve forward references
ModelDockerDeployConfigClass.model_rebuild()
ModelDockerService.model_rebuild()
ModelDockerComposeManifest.model_rebuild()
