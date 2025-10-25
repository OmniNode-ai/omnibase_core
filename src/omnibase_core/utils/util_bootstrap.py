from typing import TypeVar

"""
Core Bootstrap for ONEX Service Discovery.

Provides minimal bootstrap logic to discover and access ONEX services through
the registry node. This module contains only the essential functionality needed
to bootstrap the service discovery system.

All complex functionality has been moved to service nodes following the
registry-centric architecture pattern.
"""

from typing import Any, cast

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.utils.service_logging import ServiceLogging
from omnibase_core.utils.service_minimal_logging import ServiceMinimalLogging
from omnibase_core.utils.tool_logger_code_block import ToolLoggerCodeBlock

# Type variable for protocol types
T = TypeVar("T")


def get_service(protocol_type: type[T]) -> T | None:
    """
    Get a service implementation for the given protocol type.

    This is the main entry point for service discovery in ONEX. It attempts
    to find the registry node and use it for service resolution, with fallback
    mechanisms for bootstrap scenarios.

    Args:
        protocol_type: The protocol interface to resolve

    Returns:
        Service implementation or None if not found
    """
    try:
        # Try to get service through registry node
        registry = _get_registry_node()
        if registry:
            service = registry.get_service(protocol_type)
            # Type narrowing: cast to expected protocol type
            return service if service is not None else None
    except (
        Exception
    ):  # fallback-ok: bootstrap service discovery, fallback to minimal services
        # Registry not available, try fallback
        pass

    # Try fallback implementations
    return _get_fallback_service(protocol_type)


def get_logging_service() -> Any:
    """
    Get the logging service with special bootstrap handling.

    Returns:
        Logging service implementation
    """
    try:
        # Use registry-based logging access instead of direct imports
        registry = _get_registry_node()
        if registry:
            logger_protocol = registry.get_protocol("logger")
            if logger_protocol:
                # Return service with protocol-based access
                return ServiceLogging(logger_protocol)

        # Fallback to minimal logging if registry unavailable
        return _get_minimal_logging_service()

    except Exception:  # fallback-ok: minimal logging service unavailable
        # Fallback to minimal logging
        return _get_minimal_logging_service()


def emit_log_event(
    level: LogLevel,
    event_type: str,
    message: str,
    **kwargs: Any,
) -> None:
    """
    Bootstrap emit_log_event function.

    Routes to the appropriate logging service or provides fallback.
    """
    try:
        logging_service = get_logging_service()
        if hasattr(logging_service, "emit_log_event"):
            logging_service.emit_log_event(level, event_type, message, **kwargs)
            return
    except (
        Exception
    ):  # fallback-ok: bootstrap logging unavailable, silent fallback acceptable
        # Log to stderr as fallback when structured logging fails
        pass

    # Fallback to stderr when structured logging unavailable
    return


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    event_type: str = "generic",
    **kwargs: Any,
) -> None:
    """
    Bootstrap emit_log_event_sync function.

    Routes to the appropriate logging service or provides fallback.
    """
    try:
        logging_service = get_logging_service()
        if hasattr(logging_service, "emit_log_event_sync"):
            logging_service.emit_log_event_sync(
                level,
                message,
                event_type,
                **kwargs,
            )
            return
    except (
        Exception
    ):  # fallback-ok: bootstrap logging unavailable, silent fallback acceptable
        pass

    # Fallback to stderr when structured logging unavailable
    return


# Private helper functions


def _get_registry_node() -> Any | None:
    """
    Attempt to find and return the registry node.

    Returns:
        Registry node instance or None if not found
    """
    try:
        # Use ONEX-compliant service registry
        # DELETED: using containers now
        from omnibase_spi.spi_registry import get_spi_registry

        return get_spi_registry()

    except ImportError:
        # No registry available - ONEX systems should always have a registry
        return None


def _get_fallback_service(protocol_type: type[T]) -> T | None:
    """
    Get fallback service implementation for bootstrap scenarios.

    Args:
        protocol_type: The protocol interface to resolve

    Returns:
        Fallback service implementation or None
    """
    # Check if this is a logging protocol
    if hasattr(protocol_type, "__name__") and "Logger" in protocol_type.__name__:
        service = _get_minimal_logging_service()
        # Type narrowing: cast to T for type safety
        return cast(T, service)

    # No fallback available
    return None


def _get_minimal_logging_service() -> Any:
    """
    Get minimal logging service for bootstrap scenarios.

    Returns:
        Minimal logging service implementation
    """

    return ServiceMinimalLogging()


def is_service_available(protocol_type: type[T]) -> bool:
    """
    Check if a service is available for the given protocol type.

    Args:
        protocol_type: The protocol interface to check

    Returns:
        True if service is available, False otherwise
    """
    return get_service(protocol_type) is not None


def get_available_services() -> list[str]:
    """
    Get list of available services.

    Returns:
        List of available service types
    """
    try:
        registry = _get_registry_node()
        if registry and hasattr(registry, "list_services"):
            services = registry.list_services()
            # Type narrowing: ensure list[str]
            return list(services) if services else []
    except (
        Exception
    ):  # fallback-ok: bootstrap registry unavailable, return minimal services
        pass

    # Return minimal list for bootstrap
    return ["logging"]
