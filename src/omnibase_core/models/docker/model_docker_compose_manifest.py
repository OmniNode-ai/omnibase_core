"""Docker Compose Manifest Model.

Top-level Pydantic model for complete docker-compose.yaml validation.
Integrates all existing Docker models into unified composition structure.
"""

from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.docker.model_docker_config_file import ModelDockerConfigFile
from omnibase_core.models.docker.model_docker_network_config import (
    ModelDockerNetworkConfig,
)
from omnibase_core.models.docker.model_docker_secret_file import ModelDockerSecretFile
from omnibase_core.models.docker.model_docker_service import ModelDockerService
from omnibase_core.models.docker.model_docker_volume_config import (
    ModelDockerVolumeConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.type_serializable_value import (
    SerializedDict,
)


class ModelDockerComposeManifest(BaseModel):
    """Top-level Docker Compose manifest for complete docker-compose.yaml validation.

    This model integrates all existing Docker sub-models into a unified composition
    structure that can validate and manipulate complete docker-compose.yaml files.

    Example:
        ```python
        # Load from YAML
        manifest = ModelDockerComposeManifest.from_yaml(
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

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=3, minor=8, patch=0),
        description="Docker Compose version",
    )
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

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, v: Any) -> ModelSemVer:
        """Validate Docker Compose version format and convert to ModelSemVer.

        Docker Compose uses versions like "3.8" or "3" (major.minor format).
        This validator converts them to ModelSemVer by adding patch=0.

        Handles YAML inputs that may parse as int/float (e.g., `version: 3` or `version: 3.8`).

        Args:
            v: Version string, numeric value, or ModelSemVer to validate

        Returns:
            ModelSemVer instance

        Raises:
            ModelOnexError: If version format is invalid (VALIDATION_ERROR)
        """
        # If already ModelSemVer, return as-is
        if isinstance(v, ModelSemVer):
            return v

        # Handle None explicitly with clear error
        if v is None:
            raise ModelOnexError(
                message="Version cannot be None; expected string, number, or ModelSemVer",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Handle boolean explicitly (must check before int, as bool is subclass of int)
        if isinstance(v, bool):
            raise ModelOnexError(
                message=f"Invalid version type: bool (value={v}); expected string, number, or ModelSemVer",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Handle sequence types (list, tuple, set, frozenset)
        if isinstance(v, (list, tuple, set, frozenset)):
            type_name = type(v).__name__
            value_preview = str(v)[:100]  # Limit preview length
            raise ModelOnexError(
                message=f"Invalid version type: {type_name} (value={value_preview}); expected string, number, or ModelSemVer (not a sequence)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Handle dict input (e.g., version: {major: 3, minor: 8} from malformed YAML)
        if isinstance(v, dict):
            raise ModelOnexError(
                message=f"Invalid version type: dict (keys={list(v.keys())}); expected string, number, or ModelSemVer (not a dict)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Handle bytes input (e.g., from binary data or malformed encoding)
        if isinstance(v, (bytes, bytearray)):
            type_name = type(v).__name__
            raise ModelOnexError(
                message=f"Invalid version type: {type_name}; expected string, number, or ModelSemVer (not binary data)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Handle complex numbers (unlikely but possible programmatically)
        if isinstance(v, complex):
            raise ModelOnexError(
                message=f"Invalid version type: complex (value={v}); expected string, number, or ModelSemVer (not complex number)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Convert numeric types to string (common YAML pattern: version: 3 or version: 3.8)
        if isinstance(v, (int, float)):
            # Validate numeric range is reasonable for version numbers
            if not (-1000 <= v <= 1000):
                raise ModelOnexError(
                    message=f"Invalid version number: {v}; version components must be between -1000 and 1000",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            v = str(v)

        # Type check: ensure we now have a string
        if not isinstance(v, str):
            raise ModelOnexError(
                message=f"Invalid version type: {type(v).__name__}; expected string, number, or ModelSemVer",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Parse Docker Compose version string (e.g., "3.8", "3", "2.4")
        parts = v.split(".")
        if not all(part.isdigit() for part in parts):
            raise ModelOnexError(
                message=f"Invalid version format: {v}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Convert to ModelSemVer (add patch=0 if not present)
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return ModelSemVer(major=major, minor=minor, patch=patch)

    @model_validator(mode="after")
    def validate_service_references(self) -> "ModelDockerComposeManifest":
        """Validate that service references (networks, volumes, depends_on) exist.

        Returns:
            Validated manifest

        Raises:
            ModelOnexError: If service dependencies reference undefined services (VALIDATION_FAILED)
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
                for dep in service.depends_on:
                    if dep not in self.services:
                        errors.append(
                            f"Service '{service_name}' depends on "
                            f"undefined service '{dep}'"
                        )

        if errors:
            raise ModelOnexError(
                message="Service reference validation failed:\n" + "\n".join(errors),
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

        return self

    def get_service(self, name: str) -> ModelDockerService:
        """Get service by name.

        Args:
            name: Service name

        Returns:
            Service definition

        Raises:
            ModelOnexError: If service not found
        """
        if name not in self.services:
            raise ModelOnexError(
                message=f"Service '{name}' not found",
                error_code=EnumCoreErrorCode.RESOURCE_NOT_FOUND,
            )
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
    def from_yaml(cls, yaml_path: Path) -> "ModelDockerComposeManifest":
        """Load Docker Compose manifest from YAML file.

        Args:
            yaml_path: Path to docker-compose.yaml file

        Returns:
            Loaded manifest

        Raises:
            ModelOnexError: If YAML file doesn't exist or is invalid
        """
        if not yaml_path.exists():
            raise ModelOnexError(
                message=f"YAML file not found: {yaml_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            )

        # Load YAML data
        try:
            with open(yaml_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
        except (yaml.YAMLError, OSError, ValueError, TypeError) as e:
            raise ModelOnexError(
                message=f"Failed to load YAML from {yaml_path}: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e

        if not yaml_data:
            raise ModelOnexError(
                message=f"Empty or invalid YAML file: {yaml_path}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

        # Process services: add service name to each service data for validation
        if "services" in yaml_data:
            for service_name, service_data in yaml_data["services"].items():
                if service_data is None:
                    yaml_data["services"][service_name] = {"name": service_name}
                else:
                    service_data["name"] = service_name

        # Ensure null entries are converted to empty dicts for proper validation
        for section in ["networks", "volumes", "configs", "secrets"]:
            if yaml_data.get(section):
                for key, value in yaml_data[section].items():
                    if value is None:
                        yaml_data[section][key] = {}

        # Validate with Pydantic
        return cls.model_validate(yaml_data)

    def save_to_yaml(self, yaml_path: Path) -> None:
        """Save Docker Compose manifest to YAML file.

        Args:
            yaml_path: Path to output docker-compose.yaml file
        """
        # Convert to dict for YAML serialization
        # Serialize version as Docker Compose format (major.minor, no patch)
        version_str = f"{self.version.major}.{self.version.minor}"
        data: SerializedDict = {
            "version": version_str,
        }

        if self.name:
            data["name"] = self.name

        # Convert services
        if self.services:
            services_data: SerializedDict = {}
            for service_name, service in self.services.items():
                # Convert dataclass to dict, exclude None values
                service_dict: SerializedDict = {}
                # Include version (required field)
                service_dict["version"] = {
                    "major": service.version.major,
                    "minor": service.version.minor,
                    "patch": service.version.patch,
                }
                if service.image:
                    service_dict["image"] = service.image
                if service.build:
                    service_dict["build"] = service.build.model_dump(exclude_none=True)
                if service.command:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["command"] = cast(JsonType, service.command)
                if service.environment:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["environment"] = cast(JsonType, service.environment)
                if service.ports:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["ports"] = cast(JsonType, service.ports)
                if service.volumes:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["volumes"] = cast(JsonType, service.volumes)
                if service.depends_on:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["depends_on"] = cast(JsonType, service.depends_on)
                if service.healthcheck:
                    service_dict["healthcheck"] = service.healthcheck.model_dump(
                        exclude_none=True
                    )
                if service.restart:
                    service_dict["restart"] = service.restart
                if service.networks:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["networks"] = cast(JsonType, service.networks)
                if service.labels:
                    # Cast to JsonType (no copy needed - types are compatible at runtime)
                    service_dict["labels"] = cast(JsonType, service.labels)
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
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
