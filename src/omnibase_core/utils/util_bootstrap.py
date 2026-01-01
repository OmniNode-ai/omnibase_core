"""
Core Bootstrap for ONEX Service Discovery.

Provides minimal bootstrap logic to discover and access ONEX services through
the registry node. This module contains only the essential functionality needed
to bootstrap the service discovery system.

All complex functionality has been moved to service nodes following the
registry-centric architecture pattern.
"""

from collections.abc import Callable
from typing import cast

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.protocols.logging import ProtocolRegistryNode


class _BootstrapMinimalLogger:
    """Minimal no-op logger for bootstrap phase only."""

    @staticmethod
    def emit_log_event(  # stub-ok: Intentional no-op for minimal bootstrap logger
        level: LogLevel,
        event_type: str,
        message: str,
        **kwargs: object,
    ) -> None:
        """No-op emit_log_event for bootstrap fallback."""

    @staticmethod
    def emit_log_event_sync(  # stub-ok: Intentional no-op for minimal bootstrap logger
        level: LogLevel,
        message: str,
        event_type: str = "generic",
        **kwargs: object,
    ) -> None:
        """No-op emit_log_event_sync for bootstrap fallback."""

    @staticmethod
    async def emit_log_event_async(  # stub-ok: Intentional no-op for minimal bootstrap logger
        level: LogLevel,
        message: str,
        event_type: str = "generic",
        **kwargs: object,
    ) -> None:
        """No-op emit_log_event_async for bootstrap fallback."""

    @staticmethod
    def trace_function_lifecycle[F: Callable[..., object]](func: F) -> F:
        """No-op decorator for bootstrap."""
        return func

    @staticmethod
    def tool_logger_performance_metrics[F: Callable[..., object]](
        _threshold_ms: int = 1000,
    ) -> Callable[[F], F]:
        """Minimal tool logger performance metrics decorator."""

        def decorator(func: F) -> F:
            return func

        return decorator


def get_service[T](protocol_type: type[T]) -> T | None:
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
        pass

    # Try fallback implementations
    return _get_fallback_service(protocol_type)


def get_logging_service() -> object:
    """
    Get the logging service with special bootstrap handling.

    Returns:
        Logging service implementation (protocol or minimal fallback)
    """
    try:
        registry = _get_registry_node()
        if registry:
            logger_protocol = registry.get_protocol("logger")
            if logger_protocol:
                # Return protocol directly (no wrapper needed)
                return logger_protocol
    except Exception:  # fallback-ok: minimal logging service unavailable
        pass

    # Return inline minimal logger for bootstrap
    return _BootstrapMinimalLogger()


def emit_log_event(
    level: LogLevel,
    event_type: str,
    message: str,
    **kwargs: object,
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
        pass

    # Fallback to stderr when structured logging unavailable
    return


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    event_type: str = "generic",
    **kwargs: object,
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


def _get_registry_node() -> ProtocolRegistryNode | None:
    """
    Attempt to find and return the registry node.

    NOTE: omnibase_spi was removed in v0.3.6 - SPI now depends on Core.
    Registry discovery now happens through Core's native mechanisms
    via ModelONEXContainer. This function returns None to trigger
    fallback service resolution.

    Returns:
        Registry node instance or None if not found
    """
    # v0.3.6: SPI dependency removed - registry discovery is now handled
    # through Core's native container-based DI system.
    # Return None to use fallback service resolution.
    return None


def _get_fallback_service[T](protocol_type: type[T]) -> T | None:
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
        return cast("T", service)

    # No fallback available
    return None


def _get_minimal_logging_service() -> _BootstrapMinimalLogger:
    """
    Get minimal logging service for bootstrap scenarios.

    Returns:
        Minimal logging service implementation
    """
    return _BootstrapMinimalLogger()


def is_service_available[T](protocol_type: type[T]) -> bool:
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
        if registry:
            services = registry.list_services()
            # Type narrowing: ensure list[str]
            return list(services) if services else []
    except (
        Exception
    ):  # fallback-ok: bootstrap registry unavailable, return minimal services
        pass

    # Return minimal list for bootstrap
    return ["logging"]
