"""
Standalone ONEX Dependency Injection Container for testing.

This is a minimal version of ONEXContainer that doesn't import the full framework,
allowing for testing without circular dependencies.
"""

import os
from typing import Any, TypeVar

T = TypeVar("T")


class CoreErrorCode:
    """Core error codes for ONEX system."""

    SERVICE_RESOLUTION_FAILED = "ONEX_CORE_091_SERVICE_RESOLUTION_FAILED"


class OnexError(Exception):
    """Standard ONEX error."""

    def __init__(self, code, message, details=None, cause=None):
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(f"[{code}] {message}")


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

        Args:
            config: Configuration dictionary to update container settings
        """
        self._config.update(config)

    def register_service(self, protocol_name: str, service: Any) -> None:
        """
        Register a service instance for a protocol.

        Args:
            protocol_name: Full protocol name (e.g., 'ProtocolEventBus')
            service: Service instance implementing the protocol
        """
        self._services[protocol_name] = service

    def get_service(self, protocol_name: str) -> Any:
        """
        Get a service by protocol name or shortcut.

        Args:
            protocol_name: Protocol name or shortcut

        Returns:
            Service instance

        Raises:
            OnexError: If service cannot be resolved
        """
        # Check direct protocol name first
        if protocol_name in self._services:
            return self._services[protocol_name]

        # Try protocol shortcuts
        shortcut_mapping = {
            "event_bus": "ProtocolEventBus",
            "logger": "ProtocolLogger",
            "health_check": "ProtocolHealthCheck",
        }

        if protocol_name in shortcut_mapping:
            full_name = shortcut_mapping[protocol_name]
            if full_name in self._services:
                return self._services[full_name]

        # Service not found
        raise OnexError(
            CoreErrorCode.SERVICE_RESOLUTION_FAILED,
            f"Unable to resolve service for protocol: {protocol_name}",
        )

    def has_service(self, protocol_name: str) -> bool:
        """
        Check if a service is registered for a protocol.

        Args:
            protocol_name: Protocol name to check

        Returns:
            True if service is registered, False otherwise
        """
        return protocol_name in self._services


def create_onex_container() -> ONEXContainer:
    """
    Create a new ONEX container with default configuration.

    Returns:
        Configured ONEXContainer instance
    """
    container = ONEXContainer()

    # Default configuration from environment
    default_config = {
        "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    container.configure(default_config)
    return container


# Global container instance
_container: ONEXContainer | None = None


def get_container() -> ONEXContainer:
    """
    Get the global container instance.

    Returns:
        Global ONEXContainer instance
    """
    global _container
    if _container is None:
        _container = create_onex_container()
    return _container
