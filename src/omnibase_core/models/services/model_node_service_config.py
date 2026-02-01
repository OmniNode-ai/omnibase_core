"""
ONEX Node Service Configuration Model.

This module provides a comprehensive Pydantic schema for ONEX node service configuration,
supporting Docker, Kubernetes, and compose file generation from contracts.
"""

import os
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_service_mode import EnumServiceMode
from omnibase_core.models.configuration.model_event_bus_config import (
    ModelEventBusConfig,
)
from omnibase_core.models.configuration.model_monitoring_config import (
    ModelMonitoringConfig,
)
from omnibase_core.models.configuration.model_resource_limits import ModelResourceLimits
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.examples.model_security_config import ModelSecurityConfig
from omnibase_core.models.health.model_health_check_config import ModelHealthCheckConfig
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_network_config import ModelNetworkConfig


class ModelNodeServiceConfig(BaseModel):
    """
    Comprehensive ONEX node service configuration model.

    This model provides complete configuration for deploying ONEX nodes as services
    with support for Docker, Kubernetes, and compose file generation.
    """

    model_config = ConfigDict(from_attributes=True)

    node_name: str = Field(
        default=..., description="Name of the ONEX node", min_length=1
    )
    node_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the node",
    )
    service_mode: EnumServiceMode = Field(
        default=EnumServiceMode.STANDALONE, description="Service deployment mode"
    )
    node_id: UUID | None = Field(
        default=None, description="Override node ID for service instance"
    )
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    event_bus: ModelEventBusConfig = Field(
        default_factory=lambda: ModelEventBusConfig(),
        description="Event bus configuration",
    )
    network: ModelNetworkConfig = Field(
        default_factory=lambda: ModelNetworkConfig(),
        description="Network configuration",
    )
    health_check: ModelHealthCheckConfig = Field(
        default_factory=lambda: ModelHealthCheckConfig(),
        description="Health check configuration",
    )
    security: ModelSecurityConfig = Field(
        default_factory=lambda: ModelSecurityConfig(),
        description="Security configuration",
    )
    monitoring: ModelMonitoringConfig = Field(
        default_factory=lambda: ModelMonitoringConfig(),
        description="Monitoring configuration",
    )
    resources: ModelResourceLimits | None = Field(
        default=None, description="Resource limits for deployment"
    )
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Additional environment variables"
    )
    docker_image: str | None = Field(
        default=None, description="Docker image name for containerized deployment"
    )
    docker_tag: str | None = Field(default="latest", description="Docker image tag")
    docker_registry: str | None = Field(default=None, description="Docker registry URL")
    kubernetes_namespace: str = Field(
        default="default", description="Kubernetes namespace"
    )
    kubernetes_service_account: str | None = Field(
        default=None, description="Kubernetes service account"
    )
    compose_project_name: str | None = Field(
        default=None, description="Docker Compose project name"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Service dependencies"
    )

    @field_validator("node_name")
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        """Validate node name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            msg = "Node name must contain only alphanumeric characters, hyphens, and underscores"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        return v

    @model_validator(mode="after")
    def validate_port_conflicts(self) -> "ModelNodeServiceConfig":
        """Validate that network port and metrics port don't conflict."""
        network_port = self.network.port if self.network else None
        metrics_port = self.monitoring.prometheus_port if self.monitoring else None
        if network_port and metrics_port and (network_port == metrics_port):
            msg = "Network port and metrics port cannot be the same"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        return self

    def get_effective_node_id(self) -> str:
        """Get the effective node ID for this service instance."""
        if self.node_id:
            return str(self.node_id)
        mode_suffix = (
            f"_{self.service_mode.value}"
            if self.service_mode != EnumServiceMode.STANDALONE
            else ""
        )
        return f"{self.node_name}_service{mode_suffix}"

    def get_environment_dict(self) -> dict[str, str]:
        """Get complete environment variables for deployment."""
        env = {
            "NODE_NAME": self.node_name,
            "NODE_VERSION": str(self.node_version),
            "NODE_ID": self.get_effective_node_id(),
            "LOG_LEVEL": self.log_level.value,
            "DEBUG_MODE": str(self.debug_mode).lower(),
            "EVENT_BUS_BOOTSTRAP_SERVERS": ",".join(self.event_bus.bootstrap_servers),
            "SERVICE_MODE": self.service_mode.value,
            "SERVICE_PORT": str(self.network.port),
            "SERVICE_HOST": self.network.host,
            "HEALTH_CHECK_ENABLED": str(self.health_check.enabled).lower(),
            "METRICS_ENABLED": str(self.monitoring.prometheus_enabled).lower(),
            "METRICS_PORT": str(self.monitoring.prometheus_port),
        }
        for key, value in self.environment_variables.items():
            env[key] = str(value)
        return env

    def get_docker_labels(self) -> dict[str, str]:
        """Get Docker labels for the service."""
        return {
            "onex.node.name": self.node_name,
            "onex.node.version": str(self.node_version),
            "onex.service.mode": self.service_mode.value,
            "onex.service.type": "node_service",
        }

    def get_kubernetes_labels(self) -> dict[str, str]:
        """Get Kubernetes labels for the service."""
        return {
            "app": self.node_name,
            "version": str(self.node_version),
            "component": "onex-node",
            "service-mode": self.service_mode.value,
        }

    def get_health_check_command(self) -> list[str]:
        """Get health check command for container deployment."""
        url = f"http://localhost:{self.network.port}{self.health_check.check_path}"
        return ["curl", "-f", url]

    def supports_scaling(self) -> bool:
        """Check if this service configuration supports horizontal scaling."""
        return self.node_id is None and self.service_mode in [
            EnumServiceMode.DOCKER,
            EnumServiceMode.KUBERNETES,
        ]

    @classmethod
    @standard_error_handling("Environment configuration parsing")
    def from_environment(
        cls, node_name: str, **overrides: Any
    ) -> "ModelNodeServiceConfig":
        """
        Create service configuration from environment variables.

        Args:
            node_name: Name of the ONEX node
            **overrides: Additional configuration overrides

        Returns:
            ModelNodeServiceConfig instance with environment-based configuration
        """
        env_config = {
            "node_name": node_name,
            "node_version": os.getenv("NODE_VERSION", "1.0.0"),
            "node_id": os.getenv("NODE_ID"),
            "log_level": os.getenv("LOG_LEVEL", LogLevel.INFO.value),
            "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true",
        }
        event_bus_config = ModelEventBusConfig(
            bootstrap_servers=[
                server.strip()
                for server in os.getenv(
                    "EVENT_BUS_BOOTSTRAP_SERVERS", "localhost:9092"
                ).split(",")
            ],
            topics=[
                topic.strip()
                for topic in os.getenv("EVENT_BUS_TOPICS", "onex-default").split(",")
            ],
        )
        network_config = ModelNetworkConfig(
            port=int(os.getenv("SERVICE_PORT", "8080")),
            host=os.getenv(
                "SERVICE_HOST",
                "0.0.0.0",
            ),
        )
        health_config = ModelHealthCheckConfig(
            enabled=os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true",
            check_interval_seconds=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            timeout_seconds=int(os.getenv("HEALTH_CHECK_TIMEOUT", "10")),
        )
        monitoring_config = ModelMonitoringConfig(
            prometheus_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            prometheus_port=int(os.getenv("METRICS_PORT", "9090")),
        )
        security_config = ModelSecurityConfig()
        config = {
            **env_config,
            "event_bus": event_bus_config,
            "network": network_config,
            "health_check": health_config,
            "monitoring": monitoring_config,
            "security": security_config,
            **overrides,
        }
        return cls(**config)

    @classmethod
    def for_node_registry(cls, **overrides: Any) -> "ModelNodeServiceConfig":
        """
        Create a service configuration specifically for NodeRegistry.

        Args:
            **overrides: Configuration overrides

        Returns:
            ModelNodeServiceConfig configured for NodeRegistry service
        """
        from typing import cast

        node_registry_defaults = {
            "node_name": "node_registry",
            "docker_image": "onex/node-registry",
            "network": ModelNetworkConfig(port=8081),
            "monitoring": ModelMonitoringConfig(prometheus_port=9091),
            "depends_on": ["event-bus"],
        }
        config = {**node_registry_defaults, **overrides}
        # Cast result of decorated method to preserve type
        return cast(
            "ModelNodeServiceConfig", cls.from_environment("node_registry", **config)
        )
