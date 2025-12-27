"""Registry configuration model - implements ProtocolServiceRegistryConfig."""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelServiceRegistryConfig(BaseModel):
    """
    Service registry configuration.

    Implements ProtocolServiceRegistryConfig from omnibase_spi.
    Configures registry behavior including auto-wiring, lazy loading,
    circular dependency detection, and monitoring.

    Attributes:
        registry_name: Unique registry identifier
        auto_wire_enabled: Enable automatic dependency injection
        lazy_loading_enabled: Load services on first use
        circular_dependency_detection: Detect circular dependencies
        max_resolution_depth: Maximum depth for dependency resolution
        instance_pooling_enabled: Enable instance pooling for performance
        health_monitoring_enabled: Enable service health monitoring
        performance_monitoring_enabled: Enable performance metrics collection
        configuration: Additional configuration parameters

    Example:
        ```python
        config = ModelServiceRegistryConfig(
            registry_name="main_registry",
            auto_wire_enabled=True,
            circular_dependency_detection=True,
        )
        ```
    """

    registry_name: str = Field(
        default="omnibase_core_registry",
        description="Registry identifier",
    )
    auto_wire_enabled: bool = Field(
        default=False,  # Disabled in v1.0, enable in v2.0
        description="Enable automatic dependency injection",
    )
    lazy_loading_enabled: bool = Field(
        default=True,
        description="Load services on first use",
    )
    circular_dependency_detection: bool = Field(
        default=True,
        description="Detect circular dependencies",
    )
    max_resolution_depth: int = Field(
        default=10,
        description="Maximum dependency resolution depth",
    )
    instance_pooling_enabled: bool = Field(
        default=False,  # Disabled in v1.0, enable in v2.0
        description="Enable instance pooling",
    )
    health_monitoring_enabled: bool = Field(
        default=True,
        description="Enable health monitoring",
    )
    performance_monitoring_enabled: bool = Field(
        default=True,
        description="Enable performance metrics",
    )
    configuration: SerializedDict = Field(
        default_factory=dict,
        description="Additional configuration",
    )


def create_default_registry_config() -> ModelServiceRegistryConfig:
    """
    Create default registry configuration.

    Returns:
        Default configuration for omnibase_core service registry
    """
    return ModelServiceRegistryConfig(
        registry_name="omnibase_core_registry",
        auto_wire_enabled=False,
        lazy_loading_enabled=True,
        circular_dependency_detection=True,
        max_resolution_depth=10,
        instance_pooling_enabled=False,
        health_monitoring_enabled=True,
        performance_monitoring_enabled=True,
        configuration={
            "default_lifecycle": "singleton",
            "default_scope": "global",
            "resolution_timeout_seconds": 30.0,
            "health_check_interval_seconds": 60.0,
        },
    )
