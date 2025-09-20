"""
Core Bootstrap for ONEX Service Discovery.

Provides minimal bootstrap logic to discover and access ONEX services through
the registry node. This module contains only the essential functionality needed
to bootstrap the service discovery system.

All complex functionality has been moved to service nodes following the
registry-centric architecture pattern.
"""

from typing import Any, TypeVar

from omnibase_core.core.protocols_service_creation import (
    ProtocolLoggingService,
    ProtocolRegistryService,
)
from omnibase_core.core.service_creation_factory import ServiceCreationFactory
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

# Type variable for protocol types
T = TypeVar("T")

# Global service creation factory instance
_service_factory = ServiceCreationFactory()


def get_service(protocol_type: type[T]) -> T | None:
    """
    Get a service implementation for the given protocol type.

    This is the main entry point for service discovery in ONEX. It uses
    the strategy pattern to try different service creation approaches
    based on availability and protocol requirements.

    Args:
        protocol_type: The protocol interface to resolve

    Returns:
        Service implementation or None if not found
    """
    try:
        # Update factory with current registry state
        registry = _get_registry_node()
        _service_factory.set_registry(registry)

        # Use factory to get service
        return _service_factory.get_service(protocol_type)
    except Exception:
        # Fallback to factory without registry
        _service_factory.set_registry(None)
        return _service_factory.get_service(protocol_type)


def get_logging_service() -> ProtocolLoggingService | None:
    """
    Get the logging service with special bootstrap handling.

    Returns:
        Logging service implementation
    """
    try:
        # Update factory with current registry state
        registry = _get_registry_node()
        _service_factory.set_registry(registry)

        # Use factory to get logging service
        return _service_factory.get_logging_service()
    except Exception:
        # Fallback to factory without registry
        _service_factory.set_registry(None)
        return _service_factory.get_logging_service()


def _get_registry_node() -> ProtocolRegistryService | None:
    """
    Get the registry node for service discovery.

    Returns:
        Registry node implementation or None
    """
    # Registry discovery logic would go here
    # For now, return None to use fallback mechanisms
    return None


def get_available_service_strategies() -> list[str]:
    """
    Get list of currently available service creation strategies.

    Returns:
        List of available strategy names for debugging/monitoring
    """
    try:
        registry = _get_registry_node()
        _service_factory.set_registry(registry)
        return _service_factory.get_available_strategies()
    except Exception:
        return []


def get_available_logging_strategies() -> list[str]:
    """
    Get list of currently available logging service strategies.

    Returns:
        List of available logging strategy names for debugging/monitoring
    """
    try:
        registry = _get_registry_node()
        _service_factory.set_registry(registry)
        return _service_factory.get_available_logging_strategies()
    except Exception:
        return []