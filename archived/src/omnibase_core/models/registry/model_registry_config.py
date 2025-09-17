"""
Registry Configuration Model for ONEX Configuration-Driven Registry System.

This module provides the ModelRegistryConfig for complete registry configuration
with dependency injection and tool resolution. Extracted from model_service_configuration.py
for modular architecture compliance.

Author: OmniNode Team
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.configuration.model_cache_settings import ModelCacheSettings
from omnibase_core.models.service.model_service_configuration_single import (
    ModelServiceConfiguration,
)

if TYPE_CHECKING:
    from omnibase_core.models.service.model_service_registry_config import (
        ModelServiceRegistryConfig,
    )


class ModelRegistryConfig(BaseModel):
    """Registry configuration for dependency injection and tool resolution."""

    mode: str = Field(
        "development",
        description="Registry mode (production, development, bootstrap, etc.)",
    )
    service_config: "ModelServiceRegistryConfig" = Field(
        ...,
        description="Service registry configuration",
    )
    consul_endpoint: str | None = Field(
        None,
        description="Consul endpoint for service discovery",
    )
    kafka_brokers: list[str] = Field(
        default_factory=list,
        description="Kafka broker endpoints",
    )
    redis_endpoint: str | None = Field(
        None,
        description="Redis endpoint for caching",
    )
    enable_circuit_breaker: bool = Field(
        True,
        description="Enable circuit breaker for service failures",
    )
    enable_health_checks: bool = Field(
        True,
        description="Enable health checks for services",
    )
    cache_ttl: int = Field(300, description="Cache TTL in seconds", ge=60, le=3600)

    # Tool registry configuration fields (contract-driven defaults)
    cache_enabled: bool = Field(True, description="Enable tool instance caching")
    validation_required: bool = Field(
        True,
        description="Require tool validation on creation",
    )
    health_check_timeout_ms: int = Field(
        1000,
        description="Health check timeout in milliseconds",
        ge=100,
        le=30000,
    )
    tool_class: str = Field("", description="Tool class name override for testing")
    tool_config: dict[str, str] = Field(
        default_factory=dict,
        description="Configuration passed to tool constructor",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode_exists_in_service_config(cls, v, info):
        """Ensure the mode exists in service_config.registry_modes."""
        if info.data:
            service_config = info.data.get("service_config")
            if service_config and not service_config.has_mode(v):
                msg = f"Mode '{v}' not found in service_config.registry_modes"
                raise ValueError(
                    msg,
                )
        return v

    def get(self, key: str, default=None):
        """Get configuration value with default fallback (dict-like interface)."""
        return getattr(self, key, default)

    def get_required_services_for_mode(self, mode: str) -> list[str]:
        """Get list of required services for a specific mode."""
        mode_config = self.service_config.registry_modes.get(mode)
        if not mode_config:
            return []
        return mode_config.required_services

    def get_service_config(
        self,
        service_name: str,
    ) -> ModelServiceConfiguration | None:
        """Get configuration for a specific service."""
        return self.service_config.services.get(service_name)

    def is_service_required(self, service_name: str, mode: str | None = None) -> bool:
        """Check if a service is required for a specific mode (defaults to current mode)."""
        target_mode = mode or self.mode
        required_services = self.get_required_services_for_mode(target_mode)
        return service_name in required_services

    def get_current_mode_services(self) -> list[str]:
        """Get required services for the current mode."""
        return self.get_required_services_for_mode(self.mode)

    def has_external_services_configured(self) -> bool:
        """Check if any external services (consul, kafka, redis) are configured."""
        return (
            self.consul_endpoint is not None
            or len(self.kafka_brokers) > 0
            or self.redis_endpoint is not None
        )

    def is_distributed_mode(self) -> bool:
        """Check if this is a distributed/production-like mode."""
        return (
            self.mode in ["production", "distributed"]
            or self.has_external_services_configured()
        )

    def is_development_mode(self) -> bool:
        """Check if this is a development/testing mode."""
        return self.mode in ["development", "testing", "bootstrap"]

    def get_kafka_connection_strings(self) -> list[str]:
        """Get formatted Kafka connection strings."""
        return self.kafka_brokers

    def has_kafka_configured(self) -> bool:
        """Check if Kafka brokers are configured."""
        return len(self.kafka_brokers) > 0

    def has_consul_configured(self) -> bool:
        """Check if Consul is configured."""
        return self.consul_endpoint is not None

    def has_redis_configured(self) -> bool:
        """Check if Redis is configured."""
        return self.redis_endpoint is not None

    def get_cache_settings(self) -> ModelCacheSettings:
        """Get cache configuration settings."""
        return ModelCacheSettings(
            enabled=self.redis_endpoint is not None,
            endpoint=self.redis_endpoint,
            ttl_seconds=self.cache_ttl,
        )

    def get_circuit_breaker_settings(self) -> dict[str, bool]:
        """Get circuit breaker configuration."""
        return {
            "enabled": self.enable_circuit_breaker,
            "health_checks_enabled": self.enable_health_checks,
        }

    def get_effective_cache_ttl(self) -> int:
        """Get the effective cache TTL value."""
        return self.cache_ttl

    def add_kafka_broker(self, broker: str) -> None:
        """Add a Kafka broker to the configuration."""
        if broker not in self.kafka_brokers:
            self.kafka_brokers.append(broker)

    def remove_kafka_broker(self, broker: str) -> bool:
        """Remove a Kafka broker from the configuration. Returns True if removed."""
        if broker in self.kafka_brokers:
            self.kafka_brokers.remove(broker)
            return True
        return False

    def get_service_names(self) -> list[str]:
        """Get all configured service names."""
        return self.service_config.get_service_names()

    def get_critical_services(self) -> list[str]:
        """Get critical services for the current mode."""
        return [
            name
            for name in self.get_service_names()
            if self.is_service_required(name)
            and self.get_service_config(name)
            and self.get_service_config(name).is_critical_service()
        ]


# Fix forward references for Pydantic models
try:
    ModelRegistryConfig.model_rebuild()
except Exception:
    pass  # Ignore rebuild errors during import
