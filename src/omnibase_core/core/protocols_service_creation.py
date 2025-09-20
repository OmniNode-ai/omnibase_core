"""
Service Creation Protocols.

Protocol definitions for service creation strategies, enabling type-safe
service creation patterns in the bootstrap process.
"""

from typing import Any, Protocol, TypeVar, runtime_checkable

# Type variable for protocol types
T = TypeVar("T")


@runtime_checkable
class ProtocolServiceFactory(Protocol[T]):
    """Protocol for service factory implementations."""

    def create_service(self, protocol_type: type[T]) -> T | None:
        """
        Create a service implementation for the given protocol type.

        Args:
            protocol_type: The protocol interface to create

        Returns:
            Service implementation or None if not supported
        """
        ...

    def supports_protocol(self, protocol_type: type[T]) -> bool:
        """
        Check if this factory supports the given protocol type.

        Args:
            protocol_type: The protocol interface to check

        Returns:
            True if supported, False otherwise
        """
        ...


@runtime_checkable
class ProtocolServiceCreationStrategy(Protocol):
    """Protocol for service creation strategy implementations."""

    def get_service(self, protocol_type: type[T]) -> T | None:
        """
        Get a service implementation using this strategy.

        Args:
            protocol_type: The protocol interface to resolve

        Returns:
            Service implementation or None if not found
        """
        ...

    def is_available(self) -> bool:
        """
        Check if this strategy is currently available.

        Returns:
            True if strategy can be used, False otherwise
        """
        ...

    @property
    def strategy_name(self) -> str:
        """
        Name of this strategy for identification.

        Returns:
            Strategy name
        """
        ...


@runtime_checkable
class ProtocolRegistryService(Protocol):
    """Protocol for registry-based service access."""

    def get_service(self, protocol_type: type[T]) -> T | None:
        """
        Get service from registry.

        Args:
            protocol_type: The protocol interface to resolve

        Returns:
            Service implementation or None if not found
        """
        ...

    def get_protocol(self, name: str) -> Any:
        """
        Get protocol by name.

        Args:
            name: Protocol name

        Returns:
            Protocol implementation or None if not found
        """
        ...


@runtime_checkable
class ProtocolLoggingService(Protocol):
    """Protocol for logging service implementations."""

    def emit_log_event(self, *args: Any, **kwargs: Any) -> Any:
        """Emit log event with flexible arguments."""
        ...

    def emit_log_event_sync(self, *args: Any, **kwargs: Any) -> Any:
        """Emit log event synchronously."""
        ...

    def emit_log_event_async(self, *args: Any, **kwargs: Any) -> Any:
        """Emit log event asynchronously."""
        ...

    def trace_function_lifecycle(self, func: Any) -> Any:
        """Trace function lifecycle."""
        ...

    @property
    def ToolLoggerCodeBlock(self) -> Any:
        """Tool logger code block."""
        ...

    def tool_logger_performance_metrics(self, *args: Any, **kwargs: Any) -> Any:
        """Tool logger performance metrics."""
        ...


# Export for use
__all__ = [
    "ProtocolServiceFactory",
    "ProtocolServiceCreationStrategy",
    "ProtocolRegistryService",
    "ProtocolLoggingService",
]