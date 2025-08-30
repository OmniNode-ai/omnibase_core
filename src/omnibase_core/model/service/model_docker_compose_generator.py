"""
Docker Compose Template Generator for ONEX Bootstrapped Services.

This module generates comprehensive Docker Compose configurations for ONEX service
orchestration, building on the service_004 infrastructure with specialized support
for bootstrapped tools and service discovery.

Author: OmniNode Team
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError

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

from .model_compose_service_dict import ModelComposeServiceDict
from .model_docker_build_config import ModelDockerBuildConfig
from .model_docker_deploy_config import (ModelDockerDeployConfig,
                                         ModelDockerResourceLimits,
                                         ModelDockerResources)
from .model_docker_healthcheck_config import ModelDockerHealthcheckConfig
from .model_docker_network_config import ModelDockerNetworkConfig
from .model_docker_volume_config import ModelDockerVolumeConfig
from .model_node_service_config import ModelNodeServiceConfig


# Configuration constants
class DockerComposeConfig:
    """Configuration constants for Docker Compose generation."""

    # Docker Compose version
    COMPOSE_VERSION = "3.8"

    # Infrastructure service images
    ZOOKEEPER_IMAGE = "confluentinc/cp-zookeeper:7.4.0"
    KAFKA_IMAGE = "confluentinc/cp-kafka:7.4.0"
    PROMETHEUS_IMAGE = "prom/prometheus:v2.45.0"
    GRAFANA_IMAGE = "grafana/grafana:10.0.0"
    REDIS_IMAGE = "redis:7.2-alpine"

    # Health check defaults
    DEFAULT_HEALTH_CHECK_INTERVAL = "10s"
    DEFAULT_HEALTH_CHECK_TIMEOUT = "5s"
    DEFAULT_HEALTH_CHECK_RETRIES = 3
    DEFAULT_HEALTH_CHECK_START_PERIOD = "30s"

    # Resource limits
    DEFAULT_MEMORY_LIMIT = "256M"
    DEFAULT_CPU_LIMIT = "0.5"

    # Network configuration
    DEFAULT_NETWORK_NAME = "onex-network"
    DEFAULT_BRIDGE_NAME = "onex-bridge"

    # Port assignments
    ZOOKEEPER_PORT = 2181
    KAFKA_PORT = 9092
    PROMETHEUS_PORT = 9090
    GRAFANA_PORT = 3000
    REDIS_PORT = 6379


class ServiceTier(str, Enum):
    """Service tier classification for dependency ordering."""

    INFRASTRUCTURE = "infrastructure"  # Event bus, databases, monitoring
    CORE = "core"  # Registry, discovery services
    APPLICATION = "application"  # Business logic nodes
    UTILITY = "utility"  # Tools, utilities, one-off services


@dataclass
class ServiceDependency:
    """Represents a service dependency with health check requirements."""

    service_name: str
    condition: str = (
        "service_healthy"  # service_healthy, service_started, service_completed
    )
    optional: bool = False
    tier: ServiceTier = ServiceTier.APPLICATION


@dataclass
class ComposeServiceDefinition:
    """Complete service definition for Docker Compose."""

    name: str
    image: Optional[str] = None
    build: Optional[ModelDockerBuildConfig] = None
    command: Optional[str] = None
    environment: Dict[str, str] = None
    ports: List[str] = None
    volumes: List[str] = None
    depends_on: Dict[str, Dict[str, str]] = None
    healthcheck: Optional[ModelDockerHealthcheckConfig] = None
    restart: str = "unless-stopped"
    networks: List[str] = None
    labels: Dict[str, str] = None
    deploy: Optional[ModelDockerDeployConfig] = None

    def __post_init__(self):
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


class DockerComposeGenerator:
    """Generator for Docker Compose configurations from ONEX service schemas."""

    def __init__(
        self,
        services: List[ModelNodeServiceConfig],
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
        self.service_definitions: Dict[str, ComposeServiceDefinition] = {}
        self.networks: Dict[str, ModelDockerNetworkConfig] = {}
        self.volumes: Dict[str, ModelDockerVolumeConfig] = {}

    def generate_compose_file(self) -> str:
        """
        Generate complete Docker Compose file for all services.

        Returns:
            Docker Compose YAML content as string

        Raises:
            OnexError: If required dependencies are missing
            ValueError: If configuration validation fails
        """
        if not HAS_YAML:
            raise OnexError(
                "PyYAML is required for Docker Compose generation. Install with: pip install pyyaml",
                error_code=CoreErrorCode.DEPENDENCY_MISSING,
            )

        # Validate configuration before processing
        self._validate_configuration()

        # Build service definitions
        self._build_service_definitions()

        # Add infrastructure services if requested
        if self.include_infrastructure:
            self._add_infrastructure_services()

        # Generate networks and volumes
        self._generate_networks()
        self._generate_volumes()

        # Build final compose structure
        services_dict = {}
        for name, service_model in self._services_to_dict().items():
            services_dict[name] = service_model.model_dump(exclude_none=True)

        compose_config = {
            "version": DockerComposeConfig.COMPOSE_VERSION,
            "name": self.project_name,
            "services": services_dict,
        }

        # Add networks if any
        if self.networks:
            compose_config["networks"] = {
                name: net.model_dump(exclude_none=True)
                for name, net in self.networks.items()
            }

        # Add volumes if any
        if self.volumes:
            compose_config["volumes"] = {
                name: vol.model_dump(exclude_none=True)
                for name, vol in self.volumes.items()
            }

        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)

    def _validate_configuration(self) -> None:
        """
        Validate Docker Compose configuration before generation.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate basic requirements
        if not self.services:
            raise ValueError("No services provided for Docker Compose generation")

        if not self.project_name or not self.project_name.strip():
            raise ValueError("Project name is required and cannot be empty")

        # Validate project name format (Docker Compose requirements)
        import re

        if not re.match(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$", self.project_name):
            raise ValueError(
                f"Project name '{self.project_name}' is invalid. Must be lowercase alphanumeric with hyphens only."
            )

        # Validate each service configuration
        service_names = set()
        port_conflicts = {}

        for service in self.services:
            # Check for duplicate service names
            service_name = service.node_name.replace("_", "-")
            if service_name in service_names:
                raise ValueError(f"Duplicate service name: {service_name}")
            service_names.add(service_name)

            # Validate service has required fields
            if not hasattr(service, "node_name") or not service.node_name:
                raise ValueError("Service must have a valid node_name")

            if not hasattr(service, "network") or not service.network:
                raise ValueError(
                    f"Service {service_name} must have network configuration"
                )

            # Check for port conflicts
            if hasattr(service.network, "port") and service.network.port:
                port = service.network.port
                if port in port_conflicts:
                    raise ValueError(
                        f"Port conflict: {port} is used by both {port_conflicts[port]} and {service_name}"
                    )
                port_conflicts[port] = service_name

                # Validate port range
                if not (1 <= port <= 65535):
                    raise ValueError(f"Service {service_name} has invalid port: {port}")

            # Validate monitoring ports if enabled
            if (
                hasattr(service, "monitoring")
                and service.monitoring
                and hasattr(service.monitoring, "metrics_enabled")
                and service.monitoring.metrics_enabled
            ):
                if (
                    hasattr(service.monitoring, "metrics_port")
                    and service.monitoring.metrics_port
                ):
                    metrics_port = service.monitoring.metrics_port
                    if metrics_port in port_conflicts:
                        raise ValueError(
                            f"Metrics port conflict: {metrics_port} is used by both {port_conflicts[metrics_port]} and {service_name}"
                        )
                    port_conflicts[metrics_port] = f"{service_name}-metrics"

                    if not (1 <= metrics_port <= 65535):
                        raise ValueError(
                            f"Service {service_name} has invalid metrics port: {metrics_port}"
                        )

    def _build_service_definitions(self) -> None:
        """Build service definitions from ONEX service configurations."""
        for service_config in self.services:
            service_def = self._create_service_definition(service_config)
            self.service_definitions[service_def.name] = service_def

    def _create_service_definition(
        self, config: ModelNodeServiceConfig
    ) -> ComposeServiceDefinition:
        """Create a compose service definition from ONEX service config."""
        service_name = config.node_name.replace("_", "-")

        # Build command for service execution
        # Use Path object for module path
        module_path = Path("omnibase") / "nodes" / config.node_name / "v1_0_0"
        command = f"python -m {module_path.as_posix().replace('/', '.')}"

        # Create service definition
        service_def = ComposeServiceDefinition(
            name=service_name,
            build=ModelDockerBuildConfig(context=".", dockerfile="Dockerfile"),
            command=command,
            environment=config.get_environment_dict(),
            labels=config.get_docker_labels(),
            restart="unless-stopped",
        )

        # Add port mappings
        service_def.ports.append(f"{config.network.port}:{config.network.port}")
        if config.monitoring.metrics_enabled:
            service_def.ports.append(
                f"{config.monitoring.metrics_port}:{config.monitoring.metrics_port}"
            )

        # Add health check
        if config.health_check.enabled:
            service_def.healthcheck = ModelDockerHealthcheckConfig(
                test=config.get_health_check_command(),
                interval=f"{config.health_check.interval_seconds}s",
                timeout=f"{config.health_check.timeout_seconds}s",
                retries=config.health_check.retries,
                start_period=f"{config.health_check.start_period_seconds}s",
            )

        # Add resource limits
        if config.resources:
            deploy_resources = {}
            if config.resources.memory_mb:
                deploy_resources["memory"] = f"{config.resources.memory_mb}M"
            if config.resources.cpu_cores:
                deploy_resources["cpus"] = str(config.resources.cpu_cores)
            if deploy_resources:
                limits = ModelDockerResourceLimits(
                    memory=deploy_resources.get("memory"),
                    cpus=deploy_resources.get("cpus"),
                )
                resources = ModelDockerResources(limits=limits)
                service_def.deploy = ModelDockerDeployConfig(resources=resources)

        # Add network configuration
        if config.network.network_name:
            service_def.networks.append(config.network.network_name)
        else:
            service_def.networks.append(DockerComposeConfig.DEFAULT_NETWORK_NAME)

        # Add volume mounts for TLS certificates
        if config.security.enable_tls:
            if config.security.cert_file:
                service_def.volumes.append(
                    f"{config.security.cert_file}:/app/certs/cert.pem:ro"
                )
            if config.security.key_file:
                service_def.volumes.append(
                    f"{config.security.key_file}:/app/certs/key.pem:ro"
                )
            if config.security.ca_file:
                service_def.volumes.append(
                    f"{config.security.ca_file}:/app/certs/ca.pem:ro"
                )

        # Add dependencies based on service type
        self._add_service_dependencies(service_def, config)

        return service_def

    def _add_service_dependencies(
        self, service_def: ComposeServiceDefinition, config: ModelNodeServiceConfig
    ) -> None:
        """Add service dependencies based on configuration."""
        # All services depend on event bus
        service_def.depends_on["event-bus"] = {"condition": "service_healthy"}

        # Core services depend on registry
        if config.node_name != "node_registry":
            service_def.depends_on["node-registry"] = {"condition": "service_healthy"}

        # Add explicit dependencies from config
        for dep in config.depends_on:
            service_def.depends_on[dep] = {"condition": "service_healthy"}

    def _add_infrastructure_services(self) -> None:
        """Add infrastructure services (event bus, monitoring, etc.)."""
        # Event Bus (Kafka + Zookeeper)
        self._add_event_bus_services()

        # Monitoring stack (if any service has monitoring enabled)
        if any(service.monitoring.metrics_enabled for service in self.services):
            self._add_monitoring_services()

        # Redis for caching and state
        self._add_redis_service()

    def _add_event_bus_services(self) -> None:
        """Add event bus services (Kafka + Zookeeper)."""
        # Zookeeper
        zookeeper_def = ComposeServiceDefinition(
            name="zookeeper",
            image=DockerComposeConfig.ZOOKEEPER_IMAGE,
            environment={
                "ZOOKEEPER_CLIENT_PORT": str(DockerComposeConfig.ZOOKEEPER_PORT),
                "ZOOKEEPER_TICK_TIME": "2000",
            },
            ports=[
                f"{DockerComposeConfig.ZOOKEEPER_PORT}:{DockerComposeConfig.ZOOKEEPER_PORT}"
            ],
            healthcheck={
                "test": [
                    "CMD",
                    "echo",
                    "ruok",
                    "|",
                    "nc",
                    "localhost",
                    str(DockerComposeConfig.ZOOKEEPER_PORT),
                ],
                "interval": DockerComposeConfig.DEFAULT_HEALTH_CHECK_INTERVAL,
                "timeout": DockerComposeConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
                "retries": DockerComposeConfig.DEFAULT_HEALTH_CHECK_RETRIES,
            },
            networks=[DockerComposeConfig.DEFAULT_NETWORK_NAME],
        )
        self.service_definitions["zookeeper"] = zookeeper_def

        # Kafka
        kafka_def = ComposeServiceDefinition(
            name="event-bus",
            image=DockerComposeConfig.KAFKA_IMAGE,
            environment={
                "KAFKA_BROKER_ID": "1",
                "KAFKA_ZOOKEEPER_CONNECT": f"zookeeper:{DockerComposeConfig.ZOOKEEPER_PORT}",
                "KAFKA_ADVERTISED_LISTENERS": f"PLAINTEXT://event-bus:{DockerComposeConfig.KAFKA_PORT}",
                "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
                "KAFKA_AUTO_CREATE_TOPICS_ENABLE": "true",
            },
            ports=[
                f"{DockerComposeConfig.KAFKA_PORT}:{DockerComposeConfig.KAFKA_PORT}"
            ],
            depends_on={"zookeeper": {"condition": "service_healthy"}},
            healthcheck={
                "test": [
                    "CMD",
                    "kafka-broker-api-versions",
                    "--bootstrap-server",
                    f"localhost:{DockerComposeConfig.KAFKA_PORT}",
                ],
                "interval": DockerComposeConfig.DEFAULT_HEALTH_CHECK_INTERVAL,
                "timeout": DockerComposeConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
                "retries": DockerComposeConfig.DEFAULT_HEALTH_CHECK_RETRIES,
            },
            networks=[DockerComposeConfig.DEFAULT_NETWORK_NAME],
        )
        self.service_definitions["event-bus"] = kafka_def

    def _add_monitoring_services(self) -> None:
        """Add monitoring services (Prometheus + Grafana)."""
        # Prometheus
        prometheus_def = ComposeServiceDefinition(
            name="prometheus",
            image=DockerComposeConfig.PROMETHEUS_IMAGE,
            ports=[
                f"{DockerComposeConfig.PROMETHEUS_PORT}:{DockerComposeConfig.PROMETHEUS_PORT}"
            ],
            volumes=[
                "./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml",
                "prometheus-data:/prometheus",
            ],
            command=[
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
                "--web.console.libraries=/etc/prometheus/console_libraries",
                "--web.console.templates=/etc/prometheus/consoles",
                "--web.enable-lifecycle",
            ],
            networks=[DockerComposeConfig.DEFAULT_NETWORK_NAME],
        )
        self.service_definitions["prometheus"] = prometheus_def

        # Grafana
        grafana_def = ComposeServiceDefinition(
            name="grafana",
            image=DockerComposeConfig.GRAFANA_IMAGE,
            ports=[
                f"{DockerComposeConfig.GRAFANA_PORT}:{DockerComposeConfig.GRAFANA_PORT}"
            ],
            environment={"GF_SECURITY_ADMIN_PASSWORD": "admin"},
            volumes=["grafana-data:/var/lib/grafana"],
            networks=[DockerComposeConfig.DEFAULT_NETWORK_NAME],
        )
        self.service_definitions["grafana"] = grafana_def

    def _add_redis_service(self) -> None:
        """Add Redis service for caching and state."""
        redis_def = ComposeServiceDefinition(
            name="redis",
            image=DockerComposeConfig.REDIS_IMAGE,
            ports=[
                f"{DockerComposeConfig.REDIS_PORT}:{DockerComposeConfig.REDIS_PORT}"
            ],
            command="redis-server --appendonly yes",
            volumes=["redis-data:/data"],
            healthcheck={
                "test": ["CMD", "redis-cli", "ping"],
                "interval": DockerComposeConfig.DEFAULT_HEALTH_CHECK_INTERVAL,
                "timeout": DockerComposeConfig.DEFAULT_HEALTH_CHECK_TIMEOUT,
                "retries": DockerComposeConfig.DEFAULT_HEALTH_CHECK_RETRIES,
            },
            networks=[DockerComposeConfig.DEFAULT_NETWORK_NAME],
        )
        self.service_definitions["redis"] = redis_def

    def _generate_networks(self) -> None:
        """Generate network definitions."""
        self.networks[DockerComposeConfig.DEFAULT_NETWORK_NAME] = (
            ModelDockerNetworkConfig(
                driver="bridge",
                driver_opts={
                    "com.docker.network.bridge.name": DockerComposeConfig.DEFAULT_BRIDGE_NAME
                },
            )
        )

    def _generate_volumes(self) -> None:
        """Generate volume definitions."""
        # Add volumes for persistent data
        if self.include_infrastructure:
            self.volumes["prometheus-data"] = ModelDockerVolumeConfig()
            self.volumes["grafana-data"] = ModelDockerVolumeConfig()
            self.volumes["redis-data"] = ModelDockerVolumeConfig()

        # Add volumes for services that need persistent storage
        for service_config in self.services:
            if service_config.resources and service_config.resources.storage_mb:
                volume_name = f"{service_config.node_name.replace('_', '-')}-data"
                self.volumes[volume_name] = ModelDockerVolumeConfig()

    def _services_to_dict(self) -> Dict[str, ModelComposeServiceDict]:
        """Convert service definitions to dictionary format."""
        services_dict: Dict[str, ModelComposeServiceDict] = {}

        for service_name, service_def in self.service_definitions.items():
            # Build the service dict model
            service_model = ModelComposeServiceDict()

            # Add basic service configuration
            if service_def.image:
                service_model.image = service_def.image
            if service_def.build:
                service_model.build = service_def.build.model_dump(exclude_none=True)
            if service_def.command:
                service_model.command = service_def.command

            # Add environment variables
            if service_def.environment:
                service_model.environment = service_def.environment

            # Add ports
            if service_def.ports:
                service_model.ports = service_def.ports

            # Add volumes
            if service_def.volumes:
                service_model.volumes = service_def.volumes

            # Add dependencies
            if service_def.depends_on:
                service_model.depends_on = service_def.depends_on

            # Add health check
            if service_def.healthcheck:
                service_model.healthcheck = service_def.healthcheck.model_dump(
                    exclude_none=True
                )

            # Add restart policy
            service_model.restart = service_def.restart

            # Add networks
            if service_def.networks:
                service_model.networks = service_def.networks

            # Add labels
            if service_def.labels:
                service_model.labels = service_def.labels

            # Add deploy configuration
            if service_def.deploy:
                service_model.deploy = service_def.deploy.model_dump(exclude_none=True)

            services_dict[service_name] = service_model

        return services_dict

    def generate_monitoring_config(self) -> Dict[str, str]:
        """Generate monitoring configuration files."""
        prometheus_config = {
            "global": {"scrape_interval": "15s", "evaluation_interval": "15s"},
            "scrape_configs": [],
        }

        # Add scrape configs for each service with metrics
        for service_config in self.services:
            if service_config.monitoring.metrics_enabled:
                scrape_config = {
                    "job_name": f"{service_config.node_name}-metrics",
                    "static_configs": [
                        {
                            "targets": [
                                f"{service_config.node_name.replace('_', '-')}:{service_config.monitoring.metrics_port}"
                            ]
                        }
                    ],
                }
                prometheus_config["scrape_configs"].append(scrape_config)

        return {
            "prometheus.yml": yaml.dump(prometheus_config, default_flow_style=False)
        }

    def validate_compose_file(self) -> List[str]:
        """Validate the generated compose file for common issues."""
        issues = []

        # Check for circular dependencies
        if self._has_circular_dependencies():
            issues.append("Circular dependencies detected in service definitions")

        # Check for port conflicts
        used_ports = set()
        for service_def in self.service_definitions.values():
            for port_mapping in service_def.ports:
                host_port = port_mapping.split(":")[0]
                if host_port in used_ports:
                    issues.append(f"Port conflict detected: {host_port}")
                used_ports.add(host_port)

        # Check for missing dependencies
        for service_def in self.service_definitions.values():
            for dep_name in service_def.depends_on:
                if dep_name not in self.service_definitions:
                    issues.append(
                        f"Missing dependency: {dep_name} required by {service_def.name}"
                    )

        return issues

    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies in service definitions."""
        visited = set()
        rec_stack = set()

        def _has_cycle(service_name: str) -> bool:
            visited.add(service_name)
            rec_stack.add(service_name)

            if service_name in self.service_definitions:
                for dep_name in self.service_definitions[service_name].depends_on:
                    if dep_name not in visited:
                        if _has_cycle(dep_name):
                            return True
                    elif dep_name in rec_stack:
                        return True

            rec_stack.remove(service_name)
            return False

        for service_name in self.service_definitions:
            if service_name not in visited:
                if _has_cycle(service_name):
                    return True

        return False


def generate_complete_compose_stack(
    services: List[ModelNodeServiceConfig],
    output_dir: Path,
    project_name: str = "onex-services",
) -> Dict[str, Path]:
    """
    Generate complete Docker Compose stack with all configurations.

    Args:
        services: List of ONEX service configurations
        output_dir: Directory to write compose files
        project_name: Docker Compose project name

    Returns:
        Dictionary mapping file type to file path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate main compose file
    composer = DockerComposeGenerator(services, project_name)
    compose_content = composer.generate_compose_file()

    # Write compose file
    compose_path = output_dir / "docker-compose.yml"
    compose_path.write_text(compose_content)

    # Generate monitoring configuration
    monitoring_configs = composer.generate_monitoring_config()
    monitoring_dir = output_dir / "monitoring"
    monitoring_dir.mkdir(exist_ok=True)

    generated_files = {"compose": compose_path}

    for config_name, config_content in monitoring_configs.items():
        config_path = monitoring_dir / config_name
        config_path.write_text(config_content)
        generated_files[f"monitoring_{config_name}"] = config_path

    # Generate .env file template
    env_content = f"""# Docker Compose Environment Variables for {project_name}
# Generated from ONEX service configurations

# Project Configuration
COMPOSE_PROJECT_NAME={project_name}
COMPOSE_FILE=docker-compose.yml

# Common Service Configuration
EVENT_BUS_URL=http://event-bus:9092
LOG_LEVEL=INFO
HEALTH_CHECK_INTERVAL=30

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin

# Database Configuration
REDIS_URL=redis://redis:6379

# Security Configuration (uncomment and set if using TLS)
# TLS_ENABLED=true
# TLS_CERT_FILE=/path/to/cert.pem
# TLS_KEY_FILE=/path/to/key.pem
"""

    env_path = output_dir / ".env.template"
    env_path.write_text(env_content)
    generated_files["env_template"] = env_path

    return generated_files
