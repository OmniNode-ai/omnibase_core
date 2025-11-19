"""Docker Compose Manifest Model.

Top-level Pydantic model for complete docker-compose.yaml validation.
Integrates all existing Docker models into unified composition structure.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from omnibase_core.models.docker.model_docker_build_config import ModelDockerBuildConfig
from omnibase_core.models.docker.model_docker_deploy_config import (
    ModelDockerDeployConfig,
)
from omnibase_core.models.docker.model_docker_healthcheck_config import (
    ModelDockerHealthcheckConfig,
)
from omnibase_core.models.docker.model_docker_healthcheck_test import (
    ModelDockerHealthcheckTest,
)
from omnibase_core.models.docker.model_docker_network_config import (
    ModelDockerNetworkConfig,
)
from omnibase_core.models.docker.model_docker_placement_constraints import (
    ModelDockerPlacementConstraints,
)
from omnibase_core.models.docker.model_docker_resource_limits import (
    ModelDockerResourceLimits,
)
from omnibase_core.models.docker.model_docker_resource_reservations import (
    ModelDockerResourceReservations,
)
from omnibase_core.models.docker.model_docker_resources import ModelDockerResources
from omnibase_core.models.docker.model_docker_restart_policy import (
    ModelDockerRestartPolicy,
)
from omnibase_core.models.docker.model_docker_volume_config import (
    ModelDockerVolumeConfig,
)


class ModelDockerConfigFile(BaseModel):
    """Docker config file configuration."""

    file: str | None = Field(default=None, description="Path to config file")
    external: bool | None = Field(default=False, description="External config")
    name: str | None = Field(default=None, description="Config name")


class ModelDockerSecretFile(BaseModel):
    """Docker secret file configuration."""

    file: str | None = Field(default=None, description="Path to secret file")
    external: bool | None = Field(default=False, description="External secret")
    name: str | None = Field(default=None, description="Secret name")


class ModelDockerService(BaseModel):
    """Docker Compose service definition (Pydantic version)."""

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


class ModelDockerComposeManifest(BaseModel):
    """Top-level Docker Compose manifest for complete docker-compose.yaml validation.

    This model integrates all existing Docker sub-models into a unified composition
    structure that can validate and manipulate complete docker-compose.yaml files.

    Example:
        ```python
        # Load from YAML
        manifest = ModelDockerComposeManifest.load_from_yaml(
            Path("docker-compose.yaml")
        )

        # Access services
        service = manifest.get_service("api")

        # Validate dependencies
        warnings = manifest.validate_dependencies()

        # Save to YAML
        manifest.save_to_yaml(Path("output.yaml"))
        ```
    """

    version: str = Field(default="3.8", description="Docker Compose version")
    services: dict[str, ModelDockerService] = Field(
        default_factory=dict,
        description="Service definitions",
    )
    networks: dict[str, ModelDockerNetworkConfig] = Field(
        default_factory=dict,
        description="Network configurations",
    )
    volumes: dict[str, ModelDockerVolumeConfig] = Field(
        default_factory=dict,
        description="Volume configurations",
    )
    configs: dict[str, ModelDockerConfigFile] = Field(
        default_factory=dict,
        description="Config file definitions",
    )
    secrets: dict[str, ModelDockerSecretFile] = Field(
        default_factory=dict,
        description="Secret file definitions",
    )
    name: str | None = Field(default=None, description="Docker Compose project name")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate Docker Compose version format.

        Args:
            v: Version string to validate

        Returns:
            Validated version string

        Raises:
            ValueError: If version format is invalid
        """
        # Accept versions like "3.8", "3", "2.4", etc.
        parts = v.split(".")
        if not all(part.isdigit() for part in parts):
            raise ValueError(f"Invalid version format: {v}")
        return v

    @model_validator(mode="after")
    def validate_service_references(self) -> "ModelDockerComposeManifest":
        """Validate that service references (networks, volumes, depends_on) exist.

        Returns:
            Validated manifest

        Raises:
            ValueError: If invalid references are found
        """
        errors = []

        # Validate network references
        for service_name, service in self.services.items():
            if service.networks:
                for network in service.networks:
                    if network not in self.networks:
                        errors.append(
                            f"Service '{service_name}' references "
                            f"undefined network '{network}'"
                        )

        # Validate dependency references
        for service_name, service in self.services.items():
            if service.depends_on:
                for dep in service.depends_on.keys():
                    if dep not in self.services:
                        errors.append(
                            f"Service '{service_name}' depends on "
                            f"undefined service '{dep}'"
                        )

        if errors:
            raise ValueError(
                "Service reference validation failed:\n" + "\n".join(errors)
            )

        return self

    def get_service(self, name: str) -> ModelDockerService:
        """Get service by name.

        Args:
            name: Service name

        Returns:
            Service definition

        Raises:
            KeyError: If service not found
        """
        if name not in self.services:
            raise KeyError(f"Service '{name}' not found")
        return self.services[name]

    def get_all_services(self) -> list[ModelDockerService]:
        """Get all service definitions.

        Returns:
            List of all service definitions
        """
        return list(self.services.values())

    def validate_dependencies(self) -> list[str]:
        """Validate service dependencies and detect circular dependencies.

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        # Build dependency graph
        graph: dict[str, set[str]] = {}
        for service_name, service in self.services.items():
            graph[service_name] = set()
            if service.depends_on:
                graph[service_name].update(service.depends_on.keys())

        # Check for circular dependencies using DFS
        def has_cycle(node: str, visited: set[str], rec_stack: set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited: set[str] = set()
        for service_name in graph:
            if service_name not in visited:
                rec_stack: set[str] = set()
                if has_cycle(service_name, visited, rec_stack):
                    warnings.append(
                        f"Circular dependency detected involving service '{service_name}'"
                    )

        return warnings

    def detect_port_conflicts(self) -> list[str]:
        """Detect port conflicts across services.

        Handles all Docker port formats:
        - Simple: "8080:80"
        - With IP: "127.0.0.1:8080:80"
        - With protocol: "8080:80/tcp"
        - Combined: "127.0.0.1:8080:80/tcp"

        Returns:
            List of warning messages about port conflicts
        """
        warnings = []
        port_map: dict[str, list[str]] = {}

        for service_name, service in self.services.items():
            if service.ports:
                for port_mapping in service.ports:
                    # Strip protocol suffix if present (e.g., "/tcp", "/udp")
                    port_spec = port_mapping.split("/")[0]

                    # Parse port specification
                    parts = port_spec.split(":")
                    host_port: str

                    if len(parts) == 1:
                        # Format: "8080" (host port only)
                        host_port = parts[0]
                    elif len(parts) == 2:
                        # Format: "8080:80" (host:container)
                        host_port = parts[0]
                    elif len(parts) == 3:
                        # Format: "127.0.0.1:8080:80" (ip:host:container)
                        # Use IP:host_port as the key to avoid false conflicts
                        host_port = f"{parts[0]}:{parts[1]}"
                    else:
                        # Invalid format, skip
                        continue

                    if host_port not in port_map:
                        port_map[host_port] = []
                    port_map[host_port].append(service_name)

        # Find conflicts
        for port, services in port_map.items():
            if len(services) > 1:
                warnings.append(
                    f"Port {port} is mapped by multiple services: {', '.join(services)}"
                )

        return warnings

    @classmethod
    def load_from_yaml(cls, yaml_path: Path) -> "ModelDockerComposeManifest":
        """Load Docker Compose manifest from YAML file.

        Args:
            yaml_path: Path to docker-compose.yaml file

        Returns:
            Loaded manifest

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML is invalid
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty or invalid YAML file: {yaml_path}")

        # Convert services to ModelDockerService
        services_dict = {}
        if "services" in data:
            for service_name, service_data in data["services"].items():
                # Add service name to data
                service_data["name"] = service_name
                services_dict[service_name] = ModelDockerService(**service_data)

        # Convert networks
        networks_dict = {}
        if "networks" in data:
            for network_name, network_data in data["networks"].items():
                if network_data is None:
                    network_data = {}
                networks_dict[network_name] = ModelDockerNetworkConfig(**network_data)

        # Convert volumes
        volumes_dict = {}
        if "volumes" in data:
            for volume_name, volume_data in data["volumes"].items():
                if volume_data is None:
                    volume_data = {}
                volumes_dict[volume_name] = ModelDockerVolumeConfig(**volume_data)

        # Convert configs
        configs_dict = {}
        if "configs" in data:
            for config_name, config_data in data["configs"].items():
                if config_data is None:
                    config_data = {}
                configs_dict[config_name] = ModelDockerConfigFile(**config_data)

        # Convert secrets
        secrets_dict = {}
        if "secrets" in data:
            for secret_name, secret_data in data["secrets"].items():
                if secret_data is None:
                    secret_data = {}
                secrets_dict[secret_name] = ModelDockerSecretFile(**secret_data)

        return cls(
            version=data.get("version", "3.8"),
            services=services_dict,
            networks=networks_dict,
            volumes=volumes_dict,
            configs=configs_dict,
            secrets=secrets_dict,
            name=data.get("name"),
        )

    def save_to_yaml(self, yaml_path: Path) -> None:
        """Save Docker Compose manifest to YAML file.

        Args:
            yaml_path: Path to output docker-compose.yaml file
        """
        # Convert to dict for YAML serialization
        data: dict[str, Any] = {
            "version": self.version,
        }

        if self.name:
            data["name"] = self.name

        # Convert services
        if self.services:
            services_data: dict[str, Any] = {}
            for service_name, service in self.services.items():
                # Convert dataclass to dict, exclude None values
                service_dict: dict[str, Any] = {}
                if service.image:
                    service_dict["image"] = service.image
                if service.build:
                    service_dict["build"] = service.build.model_dump(exclude_none=True)
                if service.command:
                    service_dict["command"] = service.command
                if service.environment:
                    service_dict["environment"] = service.environment
                if service.ports:
                    service_dict["ports"] = service.ports
                if service.volumes:
                    service_dict["volumes"] = service.volumes
                if service.depends_on:
                    service_dict["depends_on"] = service.depends_on
                if service.healthcheck:
                    service_dict["healthcheck"] = service.healthcheck.model_dump(
                        exclude_none=True
                    )
                if service.restart:
                    service_dict["restart"] = service.restart
                if service.networks:
                    service_dict["networks"] = service.networks
                if service.labels:
                    service_dict["labels"] = service.labels
                if service.deploy:
                    service_dict["deploy"] = service.deploy.model_dump(
                        exclude_none=True
                    )

                services_data[service_name] = service_dict
            data["services"] = services_data

        # Convert networks
        if self.networks:
            data["networks"] = {
                name: network.model_dump(exclude_none=True)
                for name, network in self.networks.items()
            }

        # Convert volumes
        if self.volumes:
            data["volumes"] = {
                name: volume.model_dump(exclude_none=True)
                for name, volume in self.volumes.items()
            }

        # Convert configs
        if self.configs:
            data["configs"] = {
                name: config.model_dump(exclude_none=True)
                for name, config in self.configs.items()
            }

        # Convert secrets
        if self.secrets:
            data["secrets"] = {
                name: secret.model_dump(exclude_none=True)
                for name, secret in self.secrets.items()
            }

        # Write to YAML
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# Rebuild models to resolve forward references
ModelDockerService.model_rebuild()
ModelDockerComposeManifest.model_rebuild()
