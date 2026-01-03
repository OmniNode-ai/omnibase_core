"""
Docker Template Generator for ONEX Node Services.

This module generates Docker and Docker Compose configurations from service schemas,
enabling contract-driven deployment infrastructure.

"""

from pathlib import Path

from omnibase_core.models.services.model_kubernetestemplategenerator import (
    ModelKubernetesTemplateGenerator,
)
from omnibase_core.models.services.model_node_service_config import (
    ModelNodeServiceConfig,
)
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.utils.util_safe_yaml_loader import serialize_data_to_yaml


class ModelDockerTemplateGenerator:
    """Generator for Docker-related deployment templates."""

    def __init__(self, service_config: ModelNodeServiceConfig):
        """Initialize generator with service configuration."""
        self.config = service_config

    def generate_dockerfile(self, base_image: str = "python:3.11-slim") -> str:
        """
        Generate Dockerfile content for the service.

        Args:
            base_image: Base Docker image to use

        Returns:
            Dockerfile content as string
        """
        env_vars = self.config.get_environment_dict()
        labels = self.config.get_docker_labels()

        dockerfile_content = f"""# Auto-generated Dockerfile for {self.config.node_name}
# Generated from ONEX service configuration schema

FROM {base_image}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/list[Any]s/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the ONEX package
RUN pip install -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash onex
RUN chown -R onex:onex /app
USER onex

# Set environment variables
"""

        # Add environment variables
        for key, value in env_vars.items():
            dockerfile_content += f'ENV {key}="{value}"\n'

        dockerfile_content += "\n# Add Docker labels\n"
        for key, value in labels.items():
            dockerfile_content += f'LABEL {key}="{value}"\n'

        # Add port exposure
        dockerfile_content += (
            f"\n# Expose service port\nEXPOSE {self.config.network.port}\n"
        )

        if self.config.monitoring.prometheus_enabled:
            dockerfile_content += f"EXPOSE {self.config.monitoring.prometheus_port}\n"

        # Add health check
        if self.config.health_check.enabled:
            health_cmd = " ".join(self.config.get_health_check_command())
            dockerfile_content += f"""
# Health check
HEALTHCHECK --interval={self.config.health_check.check_interval_seconds}s \\
            --timeout={self.config.health_check.timeout_seconds}s \\
            CMD {health_cmd}
"""

        # Add entrypoint
        dockerfile_content += f"""
# Set entrypoint
ENTRYPOINT ["python", "-m", "omnibase.nodes.{self.config.node_name}.v1_0_0"]
"""

        return dockerfile_content

    def generate_docker_compose_service(self) -> SerializedDict:
        """
        Generate Docker Compose service definition.

        Returns:
            Docker Compose service configuration dictionary
        """
        from typing import cast

        service_name = self.config.node_name.replace("_", "-")

        # Explicitly type service_def as SerializedDict
        service_def: SerializedDict = {
            "image": f"{self.config.docker_registry or 'onex'}/{self.config.docker_image or self.config.node_name}:{self.config.docker_tag or 'latest'}",
            "container_name": f"{service_name}-{self.config.get_effective_node_id()}",
            "restart": "unless-stopped",
            "environment": dict(self.config.get_environment_dict()),
            "labels": dict(self.config.get_docker_labels()),
        }

        # Add port mappings
        ports: list[str] = [f"{self.config.network.port}:{self.config.network.port}"]
        if self.config.monitoring.prometheus_enabled:
            ports.append(
                f"{self.config.monitoring.prometheus_port}:{self.config.monitoring.prometheus_port}"
            )
        service_def["ports"] = list(ports)

        # Add health check
        if self.config.health_check.enabled:
            health_cmd = " ".join(self.config.get_health_check_command())
            service_def["healthcheck"] = {
                "test": health_cmd,
                "interval": f"{self.config.health_check.check_interval_seconds}s",
                "timeout": f"{self.config.health_check.timeout_seconds}s",
            }

        # Add resource limits
        if self.config.resources:
            deploy: SerializedDict = {}
            if self.config.resources.memory_mb or self.config.resources.cpu_cores:
                resources: SerializedDict = {}
                if self.config.resources.memory_mb:
                    resources["memory"] = f"{self.config.resources.memory_mb}M"
                if self.config.resources.cpu_cores:
                    resources["cpus"] = str(self.config.resources.cpu_cores)
                deploy["resources"] = {"limits": resources}
            service_def["deploy"] = deploy

        # Add dependencies
        if self.config.depends_on:
            service_def["depends_on"] = list(self.config.depends_on)

        # Add network configuration
        if self.config.network.network_name:
            service_def["networks"] = [self.config.network.network_name]

        # Cast the result to ensure type compatibility
        return cast(SerializedDict, {service_name: service_def})

    def generate_docker_compose_full(
        self,
        include_dependencies: bool = True,
        additional_services: SerializedDict | None = None,
    ) -> str:
        """
        Generate complete Docker Compose file with dependencies.

        Args:
            include_dependencies: Whether to include common ONEX dependencies
            additional_services: Additional services to include

        Returns:
            Complete Docker Compose YAML content
        """
        services_dict: SerializedDict = {}
        compose_config: SerializedDict = {"version": "3.8", "services": services_dict}

        # Add the main service
        for k, v in self.generate_docker_compose_service().items():
            services_dict[k] = v

        # Add common ONEX dependencies
        if include_dependencies:
            for k, v in self._get_dependency_services().items():
                services_dict[k] = v

        # Add additional services
        if additional_services:
            for k, v in additional_services.items():
                services_dict[k] = v

        # Add networks if needed
        if self.config.network.network_name:
            compose_config["networks"] = {
                self.config.network.network_name: {"driver": "bridge"},
            }

        # Add volumes for persistent data
        if self._needs_volumes():
            compose_config["volumes"] = self._get_volume_definitions()

        return serialize_data_to_yaml(
            compose_config, default_flow_style=False, sort_keys=False
        )

    def _get_dependency_services(self) -> SerializedDict:
        """Get common ONEX dependency services."""
        dependencies: SerializedDict = {}

        # Event bus service (always needed for ONEX nodes)
        dependencies["event-bus"] = {
            "image": "confluentinc/cp-kafka:latest",
            "environment": {
                "KAFKA_BROKER_ID": "1",
                "KAFKA_ZOOKEEPER_CONNECT": "zookeeper:2181",
                "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://localhost:9092",
                "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
            },
            "ports": ["9092:9092"],
            "depends_on": ["zookeeper"],
        }

        # Zookeeper (required by Kafka)
        dependencies["zookeeper"] = {
            "image": "confluentinc/cp-zookeeper:latest",
            "environment": {
                "ZOOKEEPER_CLIENT_PORT": "2181",
                "ZOOKEEPER_TICK_TIME": "2000",
            },
            "ports": ["2181:2181"],
        }

        # Redis (for caching and state)
        dependencies["redis"] = {
            "image": "redis:7-alpine",
            "ports": ["6379:6379"],
            "command": "redis-server --appendonly yes",
            "volumes": ["redis-data:/data"],
        }

        # Monitoring stack (if monitoring is enabled)
        if self.config.monitoring.prometheus_enabled:
            dependencies["prometheus"] = {
                "image": "prom/prometheus:latest",
                "ports": ["9090:9090"],
                "volumes": [
                    "./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml",
                    "prometheus-data:/prometheus",
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--web.enable-lifecycle",
                ],
            }

            dependencies["grafana"] = {
                "image": "grafana/grafana:latest",
                "ports": ["3000:3000"],
                "environment": {"GF_SECURITY_ADMIN_PASSWORD": "admin"},
                "volumes": ["grafana-data:/var/lib/grafana"],
            }

        return dependencies

    def _needs_volumes(self) -> bool:
        """Check if the service needs volume definitions."""
        return self.config.monitoring.prometheus_enabled or any(
            "redis" in dep for dep in self.config.depends_on
        )

    def _get_volume_definitions(self) -> SerializedDict:
        """Get volume definitions for the compose file."""
        volumes: SerializedDict = {}

        if self.config.monitoring.prometheus_enabled:
            volumes.update({"prometheus-data": {}, "grafana-data": {}})

        if any("redis" in dep for dep in self.config.depends_on):
            volumes["redis-data"] = {}

        return volumes


def generate_deployment_templates(
    service_config: ModelNodeServiceConfig, output_dir: Path
) -> dict[str, Path]:
    """
    Generate all deployment templates for a service configuration.

    Args:
        service_config: Service configuration model
        output_dir: Directory to write template files

    Returns:
        Dictionary mapping template type to file path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = {}

    # Generate Docker templates
    docker_gen = ModelDockerTemplateGenerator(service_config)

    # Dockerfile
    dockerfile_content = docker_gen.generate_dockerfile()
    dockerfile_path = output_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content)
    generated_files["dockerfile"] = dockerfile_path

    # Docker Compose
    compose_content = docker_gen.generate_docker_compose_full()
    compose_path = output_dir / "docker-compose.yml"
    compose_path.write_text(compose_content)
    generated_files["docker_compose"] = compose_path

    # Kubernetes templates
    k8s_gen = ModelKubernetesTemplateGenerator(service_config)
    k8s_content = k8s_gen.generate_all_manifests()
    k8s_path = output_dir / "kubernetes.yaml"
    k8s_path.write_text(k8s_content)
    generated_files["kubernetes"] = k8s_path

    return generated_files
