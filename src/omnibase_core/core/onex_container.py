"""
ONEX Dependency Injection Container.

Protocol-driven dependency injection container that provides clean service resolution
without legacy registry dependencies.

Example Usage:
    # Create and configure container
    container = create_onex_container()

    # Register services with protocols
    container.register_service("ProtocolLogger", MyLogger())
    container.register_service("ProtocolEventBus", MyEventBus())

    # Resolve services by protocol name
    logger = container.get_service("ProtocolLogger")
    event_bus = container.get_service("event_bus")  # shortcut

    # Use global singleton pattern
    global_container = get_container()
"""

import os
import threading
from typing import Any, TypeVar

from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.exceptions.base_onex_error import OnexError

T = TypeVar("T")


class ModelONEXContainer:
    """
    Protocol-driven ONEX dependency injection container.

    Provides clean dependency injection for ONEX tools and nodes using
    protocol-based service resolution without legacy registry coupling.
    """

    def __init__(self) -> None:
        """Initialize the container."""
        self._services: dict[str, Any] = {}
        self._config: dict[str, Any] = {}

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the container with settings.

        Note: This performs a shallow merge. Nested dictionaries will be
        completely replaced, not merged recursively.

        Args:
            config: Configuration dictionary to merge into container settings

        Example:
            container.configure({
                "logging": {"level": "DEBUG"},
                "database": {"host": "localhost", "port": 5432}
            })
        """
        if not isinstance(config, dict):
            raise OnexError(
                code=CoreErrorCode.INVALID_CONFIGURATION,
                message="Configuration must be a dictionary",
            )
        self._config.update(config)

    def register_service(self, protocol_name: str, service_instance: Any) -> None:
        """Register a service instance for a protocol."""
        self._services[protocol_name] = service_instance

    def get_service(self, protocol_name: str) -> Any:
        """
        Get service by protocol name.

        Clean protocol-based resolution only, without registry lookup.

        Args:
            protocol_name: Protocol interface name (e.g., "ProtocolEventBus")

        Returns:
            Service implementation instance

        Raises:
            OnexError: If service cannot be resolved
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

        # Service not found - provide enhanced error context
        available_services = list(self._services.keys())
        available_shortcuts = ["event_bus", "logger", "health_check"]

        raise OnexError(
            code=CoreErrorCode.REGISTRY_RESOLUTION_FAILED,
            message=f"Unable to resolve service for protocol: {protocol_name}",
            details={
                "requested_protocol": protocol_name,
                "available_services": available_services,
                "available_shortcuts": available_shortcuts,
                "total_services_registered": len(available_services),
            },
        )

    def has_service(self, protocol_name: str) -> bool:
        """Check if service is available for protocol."""
        return protocol_name in self._services


# === CONTAINER FACTORY ===


def create_onex_container() -> ModelONEXContainer:
    """
    Create and configure ONEX container.

    Returns configured container with basic service setup.

    Note: For SPI compliance, consider using create_spi_service_registry()
    from omnibase_core.core.spi_service_registry instead.
    """
    container = ModelONEXContainer()

    # Load basic configuration from environment
    config = {
        "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    container.configure(config)

    return container


# === GLOBAL CONTAINER INSTANCE ===
_container: ModelONEXContainer | None = None
_container_lock = threading.Lock()


def get_container() -> ModelONEXContainer:
    """
    Get or create global container instance (thread-safe).

    Thread-safe singleton pattern that ensures only one global container
    instance is created even in concurrent environments.

    Returns:
        Global ModelONEXContainer instance

    Example:
        # Safe to call from multiple threads
        container = get_container()
        logger = container.get_service("logger")
    """
    global _container
    if _container is None:
        with _container_lock:
            # Double-checked locking pattern
            if _container is None:
                _container = create_onex_container()
    return _container
