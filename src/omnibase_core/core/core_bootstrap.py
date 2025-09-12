"""
Core Bootstrap for ONEX Service Discovery.

Provides minimal bootstrap logic to discover and access ONEX services through
the registry node. This module contains only the essential functionality needed
to bootstrap the service discovery system.

All complex functionality has been moved to service nodes following the
registry-centric architecture pattern.
"""

from typing import Any, TypeVar

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

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
            return registry.get_service(protocol_type)
    except Exception:
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
                class LoggingService:
                    def __init__(self, protocol: Any) -> None:
                        self._protocol = protocol

                    def emit_log_event(self, *args: Any, **kwargs: Any) -> Any:
                        return self._protocol.emit_log_event(*args, **kwargs)

                    def emit_log_event_sync(self, *args: Any, **kwargs: Any) -> Any:
                        return self._protocol.emit_log_event_sync(*args, **kwargs)

                    def emit_log_event_async(self, *args: Any, **kwargs: Any) -> Any:
                        return self._protocol.emit_log_event_async(*args, **kwargs)

                    def trace_function_lifecycle(self, func: Any) -> Any:
                        return self._protocol.trace_function_lifecycle(func)

                    @property
                    def ToolLoggerCodeBlock(self) -> Any:
                        return self._protocol.ToolLoggerCodeBlock

                    def tool_logger_performance_metrics(
                        self,
                        *args: Any,
                        **kwargs: Any,
                    ) -> Any:
                        return self._protocol.tool_logger_performance_metrics(
                            *args,
                            **kwargs,
                        )

                return LoggingService(logger_protocol)

        # Fallback to minimal logging if registry unavailable
        return _get_minimal_logging_service()

    except Exception:
        # Fallback to minimal logging
        return _get_minimal_logging_service()


def emit_log_event(
    level: LogLevel,
    event_type: str,
    message: str,
    **kwargs,
) -> None:
    """
    Bootstrap emit_log_event function.

    Routes to the appropriate logging service or provides fallback.
    """
    try:
        logging_service = get_logging_service()
        if hasattr(logging_service, "emit_log_event"):
            return logging_service.emit_log_event(level, event_type, message, **kwargs)
    except Exception:
        # Log to stderr as fallback when structured logging fails
        pass

    # Fallback to stderr when structured logging unavailable


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    event_type: str = "generic",
    **kwargs,
) -> None:
    """
    Bootstrap emit_log_event_sync function.

    Routes to the appropriate logging service or provides fallback.
    """
    try:
        logging_service = get_logging_service()
        if hasattr(logging_service, "emit_log_event_sync"):
            return logging_service.emit_log_event_sync(
                level,
                message,
                event_type,
                **kwargs,
            )
    except Exception:
        pass

    # Fallback to stderr when structured logging unavailable


# Private helper functions


def _get_registry_node() -> Any | None:
    """
    Attempt to find and return the registry node.

    Returns:
        Registry node instance or None if not found
    """
    try:
        # Use modern tools registry directly (no migration complexity)
        from omnibase_core.tools.registry.tool_node_discovery.v1_0_0 import (
            RegistryToolNodeDiscovery,
            ToolNodeDiscoveryNode,
        )

        registry = RegistryToolNodeDiscovery()
        return ToolNodeDiscoveryNode(registry=registry)

    except ImportError:
        # Fallback to alternative implementation if primary tools not available
        try:
            from omnibase_core.nodes.node_registry.v1_0_0.node import NodeRegistry

            return NodeRegistry()
        except ImportError:
            # No registry available
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
        return _get_minimal_logging_service()

    # No fallback available
    return None


def _get_minimal_logging_service() -> Any:
    """
    Get minimal logging service for bootstrap scenarios.

    Returns:
        Minimal logging service implementation
    """

    class MinimalLoggingService:
        @staticmethod
        def emit_log_event(
            level: LogLevel,
            event_type: str,
            message: str,
            **kwargs: Any,
        ) -> None:
            pass

        @staticmethod
        def emit_log_event_sync(
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: Any,
        ) -> None:
            pass

        @staticmethod
        async def emit_log_event_async(
            level: LogLevel,
            message: str,
            event_type: str = "generic",
            **kwargs: Any,
        ) -> None:
            pass

        @staticmethod
        def trace_function_lifecycle(func: Any) -> Any:
            # No-op decorator for bootstrap
            return func

        class ToolLoggerCodeBlock:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def __enter__(self) -> Any:
                return self

            def __exit__(self, *args: Any) -> None:
                pass

        @staticmethod
        def tool_logger_performance_metrics(threshold_ms: int = 1000) -> Any:
            def decorator(func: Any) -> Any:
                return func

            return decorator

    return MinimalLoggingService()


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
            return registry.list_services()
    except Exception:
        pass

    # Return minimal list for bootstrap
    return ["logging"]
