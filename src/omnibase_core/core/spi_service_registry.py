"""
SPI-Compliant Service Registry Implementation.

Implements omnibase.protocols.container.ProtocolServiceRegistry to provide
standardized dependency injection while maintaining backward compatibility
with existing ONEXContainer usage patterns.
"""

import threading
import uuid
from datetime import datetime
from typing import Any, Type, TypeVar

from omnibase.protocols.container import (
    InjectionScope,
    ProtocolDependencyGraph,
    ProtocolInjectionContext,
    ProtocolServiceDependency,
    ProtocolServiceFactory,
    ProtocolServiceInstance,
    ProtocolServiceMetadata,
    ProtocolServiceRegistration,
    ProtocolServiceRegistry,
    ProtocolServiceRegistryConfig,
    ProtocolServiceRegistryStatus,
    ServiceHealthStatus,
    ServiceLifecycle,
    ServiceResolutionStatus,
)
from omnibase.protocols.types.core_types import (
    OperationStatus,
    ProtocolDateTime,
)

T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


class SimpleSemVer:
    """Simple semantic version implementation for SPI compliance."""

    def __init__(self, version_string: str = "1.0.0"):
        parts = version_string.split(".")
        self.major = int(parts[0]) if len(parts) > 0 else 1
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class SPIServiceRegistry:
    """
    SPI-compliant service registry that wraps ONEXContainer functionality.

    Provides a bridge between simple ONEXContainer service resolution
    and the comprehensive SPI ProtocolServiceRegistry interface.
    """

    def __init__(self) -> None:
        """Initialize the SPI service registry."""
        self._services: dict[str, Any] = {}
        self._config: dict[str, Any] = {}
        self._registrations: dict[str, ProtocolServiceRegistration] = {}
        self._instances: dict[str, list[ProtocolServiceInstance]] = {}
        self._dependency_graph: dict[str, ProtocolDependencyGraph] = {}
        self._registry_id = str(uuid.uuid4())

    # SPI ProtocolServiceRegistry properties
    @property
    def config(self) -> ProtocolServiceRegistryConfig:
        """Get registry configuration."""
        # Return a minimal config implementation
        return type(
            "Config",
            (),
            {
                "registry_name": "ONEX Service Registry",
                "max_instances": 1000,
                "enable_circular_detection": True,
                "default_lifecycle": "singleton",
                "default_scope": "global",
            },
        )()

    @property
    def registrations(self) -> dict[str, ProtocolServiceRegistration]:
        """Get all service registrations."""
        return self._registrations.copy()

    @property
    def instances(self) -> dict[str, list[ProtocolServiceInstance]]:
        """Get all service instances."""
        return self._instances.copy()

    @property
    def dependency_graph(self) -> dict[str, ProtocolDependencyGraph]:
        """Get dependency graph."""
        return self._dependency_graph.copy()

    # Backward compatibility methods (ONEXContainer interface)
    def configure(self, config: dict[str, Any]) -> None:
        """Configure the container with settings."""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        self._config.update(config)

    def register_service(self, protocol_name: str, service_instance: Any) -> str:
        """
        Register a service instance for a protocol (ONEXContainer compatibility).

        This maintains backward compatibility with existing ONEXContainer usage
        while also creating the necessary SPI registration metadata.
        """
        # Store service for ONEXContainer compatibility
        self._services[protocol_name] = service_instance

        # Create SPI-compliant registration metadata
        service_id = f"{protocol_name}_{uuid.uuid4().hex[:8]}"

        # Create minimal SPI metadata
        metadata = type(
            "ServiceMetadata",
            (),
            {
                "service_id": service_id,
                "service_name": protocol_name,
                "service_interface": protocol_name,
                "service_implementation": type(service_instance).__name__,
                "version": SimpleSemVer("1.0.0"),
                "description": f"Service for {protocol_name}",
                "tags": [],
                "configuration": {},
                "created_at": datetime.now(),
                "last_modified_at": None,
            },
        )()

        # Create SPI registration
        registration = type(
            "ServiceRegistration",
            (),
            {
                "registration_id": service_id,
                "service_metadata": metadata,
                "lifecycle": "singleton",
                "scope": "global",
                "dependencies": [],
                "registration_status": "registered",
                "health_status": "healthy",
                "registration_time": datetime.now(),
                "last_access_time": None,
                "access_count": 0,
                "instance_count": 1,
                "max_instances": None,
            },
        )()

        self._registrations[service_id] = registration

        # Create instance record
        instance = type(
            "ServiceInstance",
            (),
            {
                "instance_id": f"{service_id}_instance",
                "service_registration_id": service_id,
                "instance": service_instance,
                "lifecycle": "singleton",
                "scope": "global",
                "created_at": datetime.now(),
                "last_accessed": datetime.now(),
                "access_count": 0,
                "is_disposed": False,
                "metadata": {},
            },
        )()

        self._instances[service_id] = [instance]

        return service_id

    def get_service(self, protocol_name: str) -> Any:
        """
        Get service by protocol name (ONEXContainer compatibility).

        Maintains existing ONEXContainer behavior for backward compatibility.
        """
        # Handle direct protocol name resolution
        if protocol_name in self._services:
            return self._services[protocol_name]

        # Handle common protocol shortcuts
        protocol_shortcuts = {
            "event_bus": "ProtocolEventBus",
            "logger": "ProtocolLogger",
            "health_check": "ProtocolHealthCheck",
        }

        # Try shortcut resolution
        if protocol_name in protocol_shortcuts:
            full_protocol_name = protocol_shortcuts[protocol_name]
            if full_protocol_name in self._services:
                return self._services[full_protocol_name]

        # Service not found
        available_services = list(self._services.keys())
        available_shortcuts = ["event_bus", "logger", "health_check"]

        raise ValueError(
            f"Unable to resolve service for protocol: {protocol_name}. "
            f"Available services: {available_services}. "
            f"Available shortcuts: {available_shortcuts}"
        )

    def has_service(self, protocol_name: str) -> bool:
        """Check if service is available for protocol."""
        return protocol_name in self._services

    # Additional SPI methods (simplified implementations)
    def get_status(self) -> ProtocolServiceRegistryStatus:
        """Get registry status."""
        return type(
            "RegistryStatus",
            (),
            {
                "registry_id": self._registry_id,
                "status": "active",
                "message": "ONEX Service Registry is operational",
                "total_registrations": len(self._registrations),
                "active_instances": sum(
                    len(instances) for instances in self._instances.values()
                ),
                "failed_registrations": 0,
                "circular_dependencies": 0,
                "health_status": "healthy",
                "last_health_check": datetime.now(),
                "uptime_seconds": 0,  # Would need to track actual uptime
                "memory_usage_mb": 0,  # Would need actual memory tracking
                "metadata": {},
            },
        )()


# Factory function for creating SPI-compliant service registry
def create_spi_service_registry() -> SPIServiceRegistry:
    """Create and configure SPI-compliant service registry."""
    registry = SPIServiceRegistry()

    # Load basic configuration from environment
    import os

    config = {
        "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    registry.configure(config)
    return registry


# Global registry instance for backward compatibility
_spi_registry: SPIServiceRegistry | None = None
_registry_lock = threading.Lock()


def get_spi_registry() -> SPIServiceRegistry:
    """
    Get or create global SPI registry instance (thread-safe).

    Provides the same singleton pattern as ONEXContainer but with
    SPI compliance.
    """
    global _spi_registry
    if _spi_registry is None:
        with _registry_lock:
            # Double-checked locking pattern
            if _spi_registry is None:
                _spi_registry = create_spi_service_registry()
    return _spi_registry
