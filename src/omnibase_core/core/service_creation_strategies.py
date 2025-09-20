"""
Service Creation Strategies.

Strategy pattern implementations for service creation in the bootstrap process.
Replaces large conditionals with maintainable strategy classes.
"""

from typing import Any, TypeVar, cast

from omnibase_core.core.protocols_service_creation import (
    ProtocolLoggingService,
    ProtocolRegistryService,
    ProtocolServiceCreationStrategy,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

# Type variable for protocol types
T = TypeVar("T")


class RegistryServiceCreationStrategy:
    """Strategy for creating services through registry node."""

    def __init__(self, registry: ProtocolRegistryService | None = None) -> None:
        """Initialize strategy with optional registry."""
        self._registry = registry

    def get_service(self, protocol_type: type[T]) -> T | None:
        """Get service through registry."""
        if not self.is_available() or self._registry is None:
            return None

        try:
            service = self._registry.get_service(protocol_type)
            return service if service is not None else None
        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if registry is available."""
        return self._registry is not None

    @property
    def strategy_name(self) -> str:
        """Strategy name."""
        return "registry"


class FallbackServiceCreationStrategy:
    """Strategy for creating fallback services."""

    def get_service(self, protocol_type: type[T]) -> T | None:
        """Get fallback service implementation."""
        # For now, return None for all fallback services
        # Future implementations can add specific fallback services
        return None

    def is_available(self) -> bool:
        """Fallback is always available."""
        return True

    @property
    def strategy_name(self) -> str:
        """Strategy name."""
        return "fallback"


class MinimalLoggingServiceStrategy:
    """Strategy for creating minimal logging service."""

    def get_service(self, protocol_type: type[T]) -> T | None:
        """Get minimal logging service if requested type is logging."""
        if not self._is_logging_protocol(protocol_type):
            return None

        return cast(T, self._create_minimal_logging_service())

    def is_available(self) -> bool:
        """Minimal logging is always available."""
        return True

    @property
    def strategy_name(self) -> str:
        """Strategy name."""
        return "minimal_logging"

    def _is_logging_protocol(self, protocol_type: type[T]) -> bool:
        """Check if protocol type is logging-related."""
        # Duck typing check for logging protocols
        return (
            hasattr(protocol_type, "__name__")
            and "logging" in protocol_type.__name__.lower()
        ) or protocol_type == ProtocolLoggingService

    def _create_minimal_logging_service(self) -> ProtocolLoggingService:
        """Create minimal logging service."""

        class MinimalLoggingService:
            """Minimal logging service for bootstrap scenarios."""

            def emit_log_event(
                self, level: LogLevel, message: str, **kwargs: Any
            ) -> None:
                """Emit log event with minimal implementation."""
                print(f"[{level.value.upper()}] {message}")

            def emit_log_event_sync(
                self, level: LogLevel, message: str, **kwargs: Any
            ) -> None:
                """Emit log event synchronously."""
                self.emit_log_event(level, message, **kwargs)

            def emit_log_event_async(
                self, level: LogLevel, message: str, **kwargs: Any
            ) -> None:
                """Emit log event asynchronously."""
                self.emit_log_event(level, message, **kwargs)

            def trace_function_lifecycle(self, func: Any) -> Any:
                """Trace function lifecycle."""
                return func  # No-op for minimal implementation

            @property
            def ToolLoggerCodeBlock(self) -> Any:
                """Tool logger code block."""
                return None

            def tool_logger_performance_metrics(
                self, *args: Any, **kwargs: Any
            ) -> Any:
                """Tool logger performance metrics."""
                return None

        return MinimalLoggingService()


class ProtocolBasedLoggingServiceStrategy:
    """Strategy for creating protocol-based logging service from registry."""

    def __init__(self, registry: ProtocolRegistryService | None = None) -> None:
        """Initialize strategy with registry."""
        self._registry = registry

    def get_service(self, protocol_type: type[T]) -> T | None:
        """Get protocol-based logging service."""
        if not self.is_available() or not self._is_logging_protocol(protocol_type):
            return None

        try:
            if self._registry is None:
                return None
            logger_protocol = self._registry.get_protocol("logger")
            if not logger_protocol:
                return None

            return cast(T, self._create_protocol_logging_service(logger_protocol))
        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if registry is available."""
        return self._registry is not None

    @property
    def strategy_name(self) -> str:
        """Strategy name."""
        return "protocol_logging"

    def _is_logging_protocol(self, protocol_type: type[T]) -> bool:
        """Check if protocol type is logging-related."""
        return (
            hasattr(protocol_type, "__name__")
            and "logging" in protocol_type.__name__.lower()
        ) or protocol_type == ProtocolLoggingService

    def _create_protocol_logging_service(self, protocol: Any) -> ProtocolLoggingService:
        """Create logging service with protocol-based access."""

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
                self, *args: Any, **kwargs: Any
            ) -> Any:
                return self._protocol.tool_logger_performance_metrics(*args, **kwargs)

        return LoggingService(protocol)


# Export for use
__all__ = [
    "RegistryServiceCreationStrategy",
    "FallbackServiceCreationStrategy",
    "MinimalLoggingServiceStrategy",
    "ProtocolBasedLoggingServiceStrategy",
]