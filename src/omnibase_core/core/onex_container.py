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

# Import with fallback for isolated testing - avoids circular dependencies
try:
    from omnibase_core.core.core_error_codes import CoreErrorCode
    from omnibase_core.exceptions.base_onex_error import OnexError
except ImportError:
    # Fallback for testing isolation - minimal implementations
    class CoreErrorCode:  # type: ignore[no-redef]
        SERVICE_RESOLUTION_FAILED = "ONEX_CORE_091_SERVICE_RESOLUTION_FAILED"
        INVALID_CONFIGURATION = "ONEX_CORE_041_INVALID_CONFIGURATION"

    class OnexError(Exception):  # type: ignore[no-redef]
        def __init__(
            self,
            code: str,
            message: str,
            details: dict[str, Any] | None = None,
            cause: Exception | None = None,
        ) -> None:
            self.code = code
            self.message = message
            self.details = details or {}
            self.cause = cause
            super().__init__(f"[{code}] {message}")


T = TypeVar("T")


class ONEXContainer:
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

        # Service not found
        raise OnexError(
            code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
            message=f"Unable to resolve service for protocol: {protocol_name}",
        )

    def has_service(self, protocol_name: str) -> bool:
        """Check if service is available for protocol."""
        return protocol_name in self._services


# === CONTAINER FACTORY ===


def create_onex_container() -> ONEXContainer:
    """
    Create and configure ONEX container.

    Returns configured container with basic service setup.
    """
    container = ONEXContainer()

    # Load basic configuration from environment
    config = {
        "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    container.configure(config)

    return container


# === GLOBAL CONTAINER INSTANCE ===
_container: ONEXContainer | None = None
_container_lock = threading.Lock()


def get_container() -> ONEXContainer:
    """
    Get or create global container instance (thread-safe).

    Thread-safe singleton pattern that ensures only one global container
    instance is created even in concurrent environments.

    Returns:
        Global ONEXContainer instance

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
