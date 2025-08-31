"""
Typed configuration models for Consul integration.

Provides strongly typed configuration dictionaries to replace Dict[str, Any] usage.
"""

from typing import Any, NotRequired, TypedDict


class ConsulAgentConfig(TypedDict):
    """Configuration for Consul agent connection."""

    agent_url: str
    timeout: NotRequired[int]
    retry_attempts: NotRequired[int]
    tls_enabled: NotRequired[bool]
    tls_verify: NotRequired[bool]


class ServiceDiscoveryLayerConfig(TypedDict):
    """Configuration for a service discovery layer."""

    enabled: bool
    dns_service: NotRequired[str]
    http_api: NotRequired[str]
    timeout: NotRequired[int]
    health_check: NotRequired[bool]
    fallback_delay: NotRequired[int]
    discovery_timeout: NotRequired[int]
    default_endpoints: NotRequired[list[str]]
    connection_timeout: NotRequired[int]


class ServiceDiscoveryConfig(TypedDict):
    """Service discovery configuration."""

    layers: dict[str, ServiceDiscoveryLayerConfig]
    caching: NotRequired[dict[str, bool | int]]


class ConsulKVNamespaces(TypedDict):
    """Consul KV namespaces configuration."""

    nodes: str
    config: str
    profiles: str


class ConflictResolutionConfig(TypedDict):
    """Conflict resolution configuration."""

    strategy: str  # EnumConflictResolutionStrategy value
    timeout_ms: NotRequired[int]
    manual_resolution_required: NotRequired[bool]


class KVSyncEngineConfig(TypedDict):
    """KV sync engine configuration."""

    bidirectional: bool
    conflict_resolution: str  # EnumConflictResolutionStrategy value
    sync_interval: int
    batch_size: int


class KVValidationConfig(TypedDict):
    """KV validation configuration."""

    require_signature: bool
    hash_algorithm: str
    signature_algorithm: str
    validate_schema: NotRequired[bool]


class ConsulKVConfig(TypedDict):
    """Complete Consul KV configuration."""

    agent_url: str
    sync_engine: KVSyncEngineConfig
    validation: NotRequired[KVValidationConfig]
    namespaces: ConsulKVNamespaces
    environments: NotRequired[dict[str, dict[str, Any]]]


class ServiceRegistrationConfig(TypedDict):
    """Service registration configuration."""

    service_name: str
    service_id: str
    address: str
    port: int
    tags: NotRequired[list[str]]
    meta: NotRequired[dict[str, str]]
    check: NotRequired[dict[str, Any]]


class HealthCheckConfig(TypedDict):
    """Health check configuration."""

    name: str
    check_type: str  # memory, disk, database, kafka, etc.
    enabled: bool
    timeout: NotRequired[int]
    interval: NotRequired[int]
    threshold: NotRequired[int | float]
    warning_threshold: NotRequired[int | float]
    critical_threshold: NotRequired[int | float]
    connection_string: NotRequired[str]
    query: NotRequired[str]


class HealthEndpointConfig(TypedDict):
    """Health endpoint configuration."""

    enabled: bool
    endpoint_path: str
    checks: list[HealthCheckConfig]
    cache_ttl: NotRequired[int]
    detailed_response: NotRequired[bool]


class ServiceCommandRoutingConfig(TypedDict):
    """Service command routing configuration."""

    enabled: bool
    timeout: int
    retry_attempts: int
    load_balancing: str  # round_robin, random, etc.


class ServiceCommandErrorHandlingConfig(TypedDict):
    """Service command error handling configuration."""

    graceful_degradation: bool
    fallback_to_local: bool
    circuit_breaker_enabled: NotRequired[bool]
    failure_threshold: NotRequired[int]


class ServiceCommandsConfig(TypedDict):
    """Service commands configuration."""

    command_routing: ServiceCommandRoutingConfig
    error_handling: ServiceCommandErrorHandlingConfig


class ConfigManagementConfig(TypedDict):
    """Configuration management settings."""

    hot_reload: bool
    validation_enabled: bool
    backup_enabled: bool
    encryption_enabled: NotRequired[bool]
    compression_enabled: NotRequired[bool]


class ConsulIntegrationConfig(TypedDict):
    """Complete Consul integration configuration."""

    consul_kv: NotRequired[ConsulKVConfig]
    service_discovery: NotRequired[ServiceDiscoveryConfig]
    service_commands: NotRequired[ServiceCommandsConfig]
    health_endpoints: NotRequired[HealthEndpointConfig]
    config_management: NotRequired[ConfigManagementConfig]


# Alias for backwards compatibility
ConfigDict = dict[str, Any]
