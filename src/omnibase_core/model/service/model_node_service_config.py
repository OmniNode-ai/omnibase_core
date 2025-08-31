"""
ONEX Node Service Configuration Model.

This module provides a comprehensive Pydantic schema for ONEX node service configuration,
supporting Docker, Kubernetes, and compose file generation from contracts.

Author: OmniNode Team
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from omnibase_core.enums.events import EnumLogLevel as LogLevel
from omnibase_core.model.service.model_event_bus_config import ModelEventBusConfig
from omnibase_core.model.service.model_health_check_config import ModelHealthCheckConfig
from omnibase_core.model.service.model_monitoring_config import ModelMonitoringConfig
from omnibase_core.model.service.model_network_config import ModelNetworkConfig
from omnibase_core.model.service.model_resource_limits import ModelResourceLimits
from omnibase_core.model.service.model_security_config import ModelSecurityConfig
from omnibase_core.model.service.model_service_mode_enum import ModelServiceModeEnum

# Note: All sub-models have been moved to separate files following ONEX standards


class ModelNodeServiceConfig(BaseModel):
    """
    Comprehensive ONEX node service configuration model.

    This model provides complete configuration for deploying ONEX nodes as services
    with support for Docker, Kubernetes, and compose file generation.
    """

    # Core service identification
    node_name: str = Field(..., description="Name of the ONEX node", min_length=1)
    node_version: str = Field("1.0.0", description="Version of the node")
    service_mode: ModelServiceModeEnum = Field(
        ModelServiceModeEnum.STANDALONE,
        description="Service deployment mode",
    )

    # Environment and runtime
    node_id: str | None = Field(
        None,
        description="Override node ID for service instance",
    )
    log_level: LogLevel = Field(
        LogLevel.INFO,
        description="Logging level",
    )
    debug_mode: bool = Field(False, description="Enable debug mode")

    # Event bus configuration
    event_bus: ModelEventBusConfig = Field(
        default_factory=ModelEventBusConfig,
        description="Event bus configuration",
    )

    # Network and deployment
    network: ModelNetworkConfig = Field(
        default_factory=ModelNetworkConfig,
        description="Network configuration",
    )

    # Health monitoring
    health_check: ModelHealthCheckConfig = Field(
        default_factory=ModelHealthCheckConfig,
        description="Health check configuration",
    )

    # Security
    security: ModelSecurityConfig = Field(
        default_factory=ModelSecurityConfig,
        description="Security configuration",
    )

    # Monitoring and observability
    monitoring: ModelMonitoringConfig = Field(
        default_factory=ModelMonitoringConfig,
        description="Monitoring configuration",
    )

    # Resource management
    resources: ModelResourceLimits | None = Field(
        None,
        description="Resource limits for deployment",
    )

    # Environment variables for container deployment
    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables",
    )

    # Docker-specific configuration
    docker_image: str | None = Field(
        None,
        description="Docker image name for containerized deployment",
    )
    docker_tag: str | None = Field("latest", description="Docker image tag")
    docker_registry: str | None = Field(None, description="Docker registry URL")

    # Kubernetes-specific configuration
    kubernetes_namespace: str = Field("default", description="Kubernetes namespace")
    kubernetes_service_account: str | None = Field(
        None,
        description="Kubernetes service account",
    )

    # Compose-specific configuration
    compose_project_name: str | None = Field(
        None,
        description="Docker Compose project name",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Service dependencies",
    )

    @field_validator("node_name")
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        """Validate node name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            msg = "Node name must contain only alphanumeric characters, hyphens, and underscores"
            raise ValueError(
                msg,
            )
        return v

    @model_validator(mode="after")
    def validate_port_conflicts(self) -> "ModelNodeServiceConfig":
        """Validate that network port and metrics port don't conflict."""
        network_port = self.network.port if self.network else None
        metrics_port = self.monitoring.metrics_port if self.monitoring else None

        if network_port and metrics_port and network_port == metrics_port:
            msg = "Network port and metrics port cannot be the same"
            raise ValueError(msg)

        return self

    def get_effective_node_id(self) -> str:
        """Get the effective node ID for this service instance."""
        if self.node_id:
            return self.node_id

        # Generate service-specific node ID
        mode_suffix = (
            f"_{self.service_mode.value}"
            if self.service_mode != ModelServiceModeEnum.STANDALONE
            else ""
        )
        return f"{self.node_name}_service{mode_suffix}"

    def get_environment_dict(self) -> dict[str, str]:
        """Get complete environment variables for deployment."""
        env = {
            "NODE_NAME": self.node_name,
            "NODE_VERSION": self.node_version,
            "NODE_ID": self.get_effective_node_id(),
            "LOG_LEVEL": self.log_level.value,
            "DEBUG_MODE": str(self.debug_mode).lower(),
            "EVENT_BUS_URL": self.event_bus.url,
            "SERVICE_MODE": self.service_mode.value,
            "SERVICE_PORT": str(self.network.port),
            "SERVICE_HOST": self.network.host,
            "HEALTH_CHECK_ENABLED": str(self.health_check.enabled).lower(),
            "METRICS_ENABLED": str(self.monitoring.metrics_enabled).lower(),
            "METRICS_PORT": str(self.monitoring.metrics_port),
            "STRUCTURED_LOGGING": str(self.monitoring.log_structured).lower(),
        }

        # Add security environment variables
        if self.security.enable_tls:
            env["TLS_ENABLED"] = "true"
            if self.security.cert_file:
                env["TLS_CERT_FILE"] = str(self.security.cert_file)
            if self.security.key_file:
                env["TLS_KEY_FILE"] = str(self.security.key_file)
            if self.security.ca_file:
                env["TLS_CA_FILE"] = str(self.security.ca_file)

        # Add custom environment variables
        env.update(self.environment_variables)

        return env

    def get_docker_labels(self) -> dict[str, str]:
        """Get Docker labels for the service."""
        return {
            "onex.node.name": self.node_name,
            "onex.node.version": self.node_version,
            "onex.service.mode": self.service_mode.value,
            "onex.service.type": "node_service",
        }

    def get_kubernetes_labels(self) -> dict[str, str]:
        """Get Kubernetes labels for the service."""
        return {
            "app": self.node_name,
            "version": self.node_version,
            "component": "onex-node",
            "service-mode": self.service_mode.value,
        }

    def get_health_check_command(self) -> list[str]:
        """Get health check command for container deployment."""
        url = f"http://localhost:{self.network.port}{self.health_check.endpoint}"
        return ["curl", "-f", url]

    def supports_scaling(self) -> bool:
        """Check if this service configuration supports horizontal scaling."""
        # Services with persistent state or specific node IDs don't scale well
        return self.node_id is None and self.service_mode in [
            ModelServiceModeEnum.DOCKER,
            ModelServiceModeEnum.KUBERNETES,
        ]

    @classmethod
    def from_environment(cls, node_name: str, **overrides) -> "ModelNodeServiceConfig":
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

        # Event bus configuration from environment
        event_bus_config = {
            "url": os.getenv("EVENT_BUS_URL", "http://localhost:8083"),
            "timeout_ms": int(os.getenv("EVENT_BUS_TIMEOUT_MS", "30000")),
            "retry_attempts": int(os.getenv("EVENT_BUS_RETRY_ATTEMPTS", "3")),
        }

        # Network configuration from environment
        network_config = {
            "port": int(os.getenv("SERVICE_PORT", "8080")),
            "host": os.getenv("SERVICE_HOST", "0.0.0.0"),
        }

        # Health check configuration from environment
        health_config = {
            "enabled": os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true",
            "interval_seconds": int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            "timeout_seconds": int(os.getenv("HEALTH_CHECK_TIMEOUT", "10")),
        }

        # Monitoring configuration from environment
        monitoring_config = {
            "metrics_enabled": os.getenv("METRICS_ENABLED", "true").lower() == "true",
            "metrics_port": int(os.getenv("METRICS_PORT", "9090")),
            "log_structured": os.getenv("STRUCTURED_LOGGING", "true").lower() == "true",
        }

        # Security configuration from environment
        security_config = {
            "enable_tls": os.getenv("TLS_ENABLED", "false").lower() == "true",
        }

        if security_config["enable_tls"]:
            security_config.update(
                {
                    "cert_file": (
                        Path(cert_file)
                        if (cert_file := os.getenv("TLS_CERT_FILE"))
                        else None
                    ),
                    "key_file": (
                        Path(key_file)
                        if (key_file := os.getenv("TLS_KEY_FILE"))
                        else None
                    ),
                    "ca_file": (
                        Path(ca_file) if (ca_file := os.getenv("TLS_CA_FILE")) else None
                    ),
                },
            )

        # Build complete configuration
        config = {
            **env_config,
            "event_bus": ModelEventBusConfig(**event_bus_config),
            "network": ModelNetworkConfig(**network_config),
            "health_check": ModelHealthCheckConfig(**health_config),
            "monitoring": ModelMonitoringConfig(**monitoring_config),
            "security": ModelSecurityConfig(**security_config),
            **overrides,
        }

        return cls(**config)

    @classmethod
    def for_node_registry(cls, **overrides) -> "ModelNodeServiceConfig":
        """
        Create a service configuration specifically for NodeRegistry.

        Args:
            **overrides: Configuration overrides

        Returns:
            ModelNodeServiceConfig configured for NodeRegistry service
        """
        node_registry_defaults = {
            "node_name": "node_registry",
            "docker_image": "onex/node-registry",
            "network": ModelNetworkConfig(port=8081),  # Registry-specific port
            "monitoring": ModelMonitoringConfig(
                metrics_port=9091,
            ),  # Registry-specific metrics port
            "depends_on": ["event-bus"],  # Registry depends on event bus
        }

        config = {**node_registry_defaults, **overrides}
        return cls.from_environment("node_registry", **config)
