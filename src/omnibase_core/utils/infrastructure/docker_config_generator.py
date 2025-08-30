"""
Docker configuration generator using Pydantic models.

Generates type-safe, validated Docker configurations from Pydantic models.
"""

from pathlib import Path
from typing import Dict, List, Optional

from omnibase_core.models.infrastructure.model_docker_config import (
    DockerLogDriver, DockerNetworkDriver, DockerRestartPolicy,
    DockerVolumeDriver, ModelDockerBuildArg, ModelDockerBuildStage,
    ModelDockerCompose, ModelDockerEnvironment, ModelDockerfile,
    ModelDockerHealthCheck, ModelDockerLogging, ModelDockerNetwork,
    ModelDockerPort, ModelDockerResources, ModelDockerService,
    ModelDockerVolume, ModelDockerVolumeMount)


class DockerConfigGenerator:
    """Generate Docker configurations from Pydantic models."""

    @staticmethod
    def create_onex_service_dockerfile(
        service_name: str,
        service_group: str,
        python_version: str = "3.12",
        poetry_version: str = "1.8.5",
        dependency_group: Optional[str] = None,
        expose_ports: Optional[List[int]] = None,
        additional_env: Optional[Dict[str, str]] = None,
    ) -> ModelDockerfile:
        """
        Create a standardized ONEX service Dockerfile.

        Args:
            service_name: Name of the service (e.g., 'event_bus')
            service_group: Service group (e.g., 'services', 'tools', 'nodes')
            python_version: Python version to use
            poetry_version: Poetry version to use
            dependency_group: Optional Poetry dependency group
            expose_ports: Ports to expose
            additional_env: Additional environment variables

        Returns:
            ModelDockerfile configured for the service
        """
        expose_ports = expose_ports or [8080]
        additional_env = additional_env or {}

        # Global build arguments
        global_args = [
            ModelDockerBuildArg(
                name="PYTHON_VERSION",
                default=python_version,
                description="Python version",
            ),
            ModelDockerBuildArg(
                name="POETRY_VERSION",
                default=poetry_version,
                description="Poetry version",
            ),
            ModelDockerBuildArg(
                name="SERVICE_NAME", default=service_name, description="Service name"
            ),
            ModelDockerBuildArg(
                name="SERVICE_GROUP", default=service_group, description="Service group"
            ),
        ]

        if dependency_group:
            global_args.append(
                ModelDockerBuildArg(
                    name="DEPENDENCY_GROUP",
                    default=dependency_group,
                    description="Poetry dependency group",
                )
            )

        # Stage 1: Dependencies
        dependencies_stage = ModelDockerBuildStage(
            name="dependencies",
            from_image="python:${PYTHON_VERSION}-slim",
            workdir="/app",
            copy_commands=[
                {"source": "pyproject.toml poetry.lock", "destination": "./"}
            ],
            run_commands=["pip install --no-cache-dir poetry==${POETRY_VERSION}"],
        )

        if dependency_group:
            dependencies_stage.run_commands.append(
                f"poetry export -f requirements.txt --output requirements.txt --without-hashes --with {dependency_group}"
            )
        else:
            dependencies_stage.run_commands.append(
                "poetry export -f requirements.txt --output requirements.txt --without-hashes"
            )

        # Stage 2: Builder
        builder_stage = ModelDockerBuildStage(
            name="builder",
            from_image="python:${PYTHON_VERSION}-slim",
            workdir="/app",
            run_commands=[
                "apt-get update && apt-get install -y build-essential g++ curl cmake libssl-dev && rm -rf /var/lib/apt/lists/*",
                "python -m venv /opt/venv",
            ],
            env=[ModelDockerEnvironment(name="PATH", value="/opt/venv/bin:$PATH")],
            copy_commands=[
                {
                    "source": "/app/requirements.txt",
                    "destination": ".",
                    "from": "dependencies",
                }
            ],
        )
        builder_stage.run_commands.append(
            "pip install --no-cache-dir --upgrade pip setuptools wheel && "
            "pip install --no-cache-dir -r requirements.txt"
        )

        # Stage 3: Test (optional but included)
        test_stage = ModelDockerBuildStage(
            name="test",
            from_stage="builder",  # FROM builder AS test
            workdir="/app",
            copy_commands=[
                {"source": "src/", "destination": "./src/"},
                {"source": "tests/", "destination": "./tests/"},
            ],
            env=[ModelDockerEnvironment(name="PYTHONPATH", value="/app/src")],
            run_commands=[
                f"if [ -d 'tests/unit/{service_group}/{service_name}' ]; then "
                f"python -m pytest tests/unit/{service_group}/{service_name} -v; fi"
            ],
        )

        # Stage 4: Runtime
        runtime_env = [
            ModelDockerEnvironment(name="PATH", value="/opt/venv/bin:$PATH"),
            ModelDockerEnvironment(name="VIRTUAL_ENV", value="/opt/venv"),
            ModelDockerEnvironment(name="PYTHONPATH", value="/app/src"),
            ModelDockerEnvironment(name="PYTHONUNBUFFERED", value="1"),
            ModelDockerEnvironment(name="SERVICE_NAME", value=service_name),
            ModelDockerEnvironment(name="SERVICE_GROUP", value=service_group),
            ModelDockerEnvironment(name="ONEX_SERVICE_NAME", value=service_name),
            ModelDockerEnvironment(name="ONEX_SERVICE_GROUP", value=service_group),
            ModelDockerEnvironment(name="ONEX_LOG_LEVEL", value="INFO"),
            ModelDockerEnvironment(name="SERVICE_HOST", value="0.0.0.0"),
            ModelDockerEnvironment(name="SERVICE_PORT", value="8080"),
            ModelDockerEnvironment(
                name="EVENT_BUS_URL", value="http://onex-event-bus:8080"
            ),
            ModelDockerEnvironment(name="CONSUL_HOST", value="consul"),
            ModelDockerEnvironment(name="CONSUL_PORT", value="8500"),
        ]

        # Add additional environment variables
        for key, value in additional_env.items():
            runtime_env.append(ModelDockerEnvironment(name=key, value=value))

        runtime_stage = ModelDockerBuildStage(
            name="runtime",
            from_image="python:${PYTHON_VERSION}-slim",
            workdir="/app",
            run_commands=[
                "apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* && apt-get clean",
                "groupadd -r onex && useradd -r -g onex -u 1000 -m -s /bin/bash onex",
                "mkdir -p /app/logs /app/data /app/config /app/tmp && chown -R onex:onex /app",
            ],
            copy_commands=[
                {
                    "source": "/opt/venv",
                    "destination": "/opt/venv",
                    "from": "builder",
                    "chown": "onex:onex",
                },
                {
                    "source": "src/omnibase/core/",
                    "destination": "./src/omnibase/core/",
                    "chown": "onex:onex",
                },
                {
                    "source": "src/omnibase/enums/",
                    "destination": "./src/omnibase/enums/",
                    "chown": "onex:onex",
                },
                {
                    "source": "src/omnibase/protocol/",
                    "destination": "./src/omnibase/protocol/",
                    "chown": "onex:onex",
                },
                {
                    "source": "src/omnibase/models/",
                    "destination": "./src/omnibase/models/",
                    "chown": "onex:onex",
                },
                {
                    "source": "src/omnibase/registry/",
                    "destination": "./src/omnibase/registry/",
                    "chown": "onex:onex",
                },
                {
                    "source": "src/omnibase/utils/",
                    "destination": "./src/omnibase/utils/",
                    "chown": "onex:onex",
                },
                {
                    "source": f"src/omnibase/{service_group}/",
                    "destination": f"./src/omnibase/{service_group}/",
                    "chown": "onex:onex",
                },
            ],
            env=runtime_env,
            user="onex",
            expose=expose_ports,
            healthcheck=ModelDockerHealthCheck(
                test=[
                    "CMD",
                    "python",
                    "-c",
                    "import urllib.request; urllib.request.urlopen('http://localhost:${SERVICE_PORT:-8080}/health').read()",
                ],
                interval="30s",
                timeout="10s",
                retries=3,
                start_period="60s",
            ),
            entrypoint=["python", "-m"],
            cmd=["omnibase.services.tool_group_daemon"],
            labels={
                "maintainer": "ONEX Team",
                "version": "1.0.0",
                "description": f"ONEX {service_group}/{service_name} Service",
                "org.opencontainers.image.source": "https://github.com/OmniNode-ai/omnibase",
            },
        )

        return ModelDockerfile(
            description=f"ONEX {service_group}/{service_name} Service",
            version="1.0.0",
            global_args=global_args,
            stages=[dependencies_stage, builder_stage, test_stage, runtime_stage],
        )

    @staticmethod
    def create_tool_group_service(
        tools: List[str],
        kafka_enabled: bool = True,
        consul_enabled: bool = True,
    ) -> ModelDockerService:
        """
        Create a Docker Compose service for a tool group.

        Args:
            tools: List of tool names to include
            kafka_enabled: Whether to enable Kafka integration
            consul_enabled: Whether to enable Consul integration

        Returns:
            ModelDockerService configured for the tool group
        """
        environment = [
            ModelDockerEnvironment(name="PYTHONPATH", value="/app/src"),
            ModelDockerEnvironment(name="PYTHONUNBUFFERED", value="1"),
            ModelDockerEnvironment(
                name="ONEX_LOG_LEVEL", from_env="ONEX_LOG_LEVEL", default="INFO"
            ),
            ModelDockerEnvironment(
                name="EVENT_BUS_URL",
                from_env="EVENT_BUS_URL",
                default="http://onex-event-bus:8080",
            ),
            ModelDockerEnvironment(name="TOOL_DISCOVERY_ENABLED", value="true"),
            ModelDockerEnvironment(name="TOOL_INTROSPECTION_INTERVAL", value="60"),
            ModelDockerEnvironment(name="TOOLS_LIST", value=",".join(tools)),
        ]

        depends_on = ["onex-event-bus"]

        if kafka_enabled:
            environment.append(
                ModelDockerEnvironment(
                    name="KAFKA_BOOTSTRAP_SERVERS",
                    from_env="KAFKA_BOOTSTRAP_SERVERS",
                    default="kafka:29092",
                )
            )
            depends_on.append("kafka")

        if consul_enabled:
            environment.extend(
                [
                    ModelDockerEnvironment(
                        name="CONSUL_HOST", from_env="CONSUL_HOST", default="consul"
                    ),
                    ModelDockerEnvironment(
                        name="CONSUL_PORT", from_env="CONSUL_PORT", default="8500"
                    ),
                    ModelDockerEnvironment(
                        name="SERVICE_DISCOVERY_ENABLED", value="true"
                    ),
                ]
            )
            depends_on.append("consul")

        return ModelDockerService(
            name="onex-tool-group",
            container_name="onex-tool-group",
            hostname="onex-tool-group",
            build={
                "context": ".",
                "dockerfile": "docker/Dockerfile.standard",
                "args": {
                    "SERVICE_NAME": "tool_group",
                    "SERVICE_GROUP": "tools",
                    "DEPENDENCY_GROUP": "generation",
                },
            },
            environment=environment,
            volumes=[
                ModelDockerVolumeMount(
                    source="./src", target="/app/src", read_only=True
                ),
                ModelDockerVolumeMount(source="./logs", target="/app/logs"),
                ModelDockerVolumeMount(source="./generated", target="/app/generated"),
            ],
            depends_on=depends_on,
            networks=["onex-network"],
            restart=DockerRestartPolicy.UNLESS_STOPPED,
            healthcheck=ModelDockerHealthCheck(
                test=["CMD", "python", "-m", "omnibase.core.health_check"],
                interval="30s",
                timeout="10s",
                retries=3,
                start_period="60s",
            ),
            logging=ModelDockerLogging(
                driver=DockerLogDriver.JSON_FILE,
                options={
                    "max-size": "10m",
                    "max-file": "3",
                    "labels": "service,group,version",
                },
            ),
            labels={
                "com.onex.service": "tool-group",
                "com.onex.version": "1.0.0",
                "com.onex.environment": "development",
            },
        )

    @staticmethod
    def create_production_compose(
        services: List[ModelDockerService],
        include_monitoring: bool = True,
    ) -> ModelDockerCompose:
        """
        Create a production Docker Compose configuration.

        Args:
            services: List of services to include
            include_monitoring: Whether to include monitoring stack

        Returns:
            ModelDockerCompose configured for production
        """
        networks = [
            ModelDockerNetwork(
                name="onex-network",
                driver=DockerNetworkDriver.BRIDGE,
                ipam={"config": [{"subnet": "172.28.0.0/16"}]},
            )
        ]

        volumes = [
            ModelDockerVolume(name="postgres_data"),
            ModelDockerVolume(name="redis_data"),
            ModelDockerVolume(name="kafka_data"),
            ModelDockerVolume(name="consul_data"),
            ModelDockerVolume(name="onex_logs"),
            ModelDockerVolume(name="onex_data"),
        ]

        if include_monitoring:
            # Add Prometheus service
            prometheus = ModelDockerService(
                name="prometheus",
                image="prom/prometheus:latest",
                container_name="onex-prometheus",
                ports=[ModelDockerPort(host=9090, container=9090)],
                volumes=[
                    ModelDockerVolumeMount(
                        source="./config/prometheus",
                        target="/etc/prometheus",
                        read_only=True,
                    ),
                    ModelDockerVolumeMount(
                        source="prometheus_data", target="/prometheus", type="volume"
                    ),
                ],
                command=[
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                ],
                networks=["onex-network"],
                restart=DockerRestartPolicy.UNLESS_STOPPED,
            )
            services.append(prometheus)
            volumes.append(ModelDockerVolume(name="prometheus_data"))

            # Add Grafana service
            grafana = ModelDockerService(
                name="grafana",
                image="grafana/grafana:latest",
                container_name="onex-grafana",
                ports=[ModelDockerPort(host=3000, container=3000)],
                environment=[
                    ModelDockerEnvironment(
                        name="GF_SECURITY_ADMIN_PASSWORD",
                        from_env="GRAFANA_ADMIN_PASSWORD",
                        default="admin",
                    ),
                ],
                volumes=[
                    ModelDockerVolumeMount(
                        source="grafana_data", target="/var/lib/grafana", type="volume"
                    ),
                    ModelDockerVolumeMount(
                        source="./config/grafana/provisioning",
                        target="/etc/grafana/provisioning",
                        read_only=True,
                    ),
                ],
                networks=["onex-network"],
                restart=DockerRestartPolicy.UNLESS_STOPPED,
                depends_on=["prometheus"],
            )
            services.append(grafana)
            volumes.append(ModelDockerVolume(name="grafana_data"))

        return ModelDockerCompose(
            version="3.9",
            name="onex",
            services=services,
            networks=networks,
            volumes=volumes,
            extensions={
                "common-environment": {
                    "PYTHONPATH": "/app/src",
                    "PYTHONUNBUFFERED": "1",
                    "ONEX_LOG_LEVEL": "${ONEX_LOG_LEVEL:-INFO}",
                }
            },
        )

    @staticmethod
    def save_dockerfile(dockerfile: ModelDockerfile, path: Path) -> None:
        """Save Dockerfile to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(dockerfile.generate_dockerfile())

    @staticmethod
    def save_compose(compose: ModelDockerCompose, path: Path) -> None:
        """Save docker-compose.yml to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(compose.to_yaml())
