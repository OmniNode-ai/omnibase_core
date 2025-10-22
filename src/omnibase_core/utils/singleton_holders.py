"""
Singleton holder classes for global registry instances.

These holders support the DI container pattern with fallback mechanisms
for bootstrap and circular dependency scenarios.

This module consolidates all singleton holder classes to maintain the
single-class-per-file architectural standard while providing shared
infrastructure for global instance management.
"""

import threading
from typing import Any


class _ActionRegistryHolder:
    """Thread-safe action registry singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get registry instance."""
        return cls._instance

    @classmethod
    def set(cls, registry: Any) -> None:
        """Set registry instance."""
        cls._instance = registry


class _EventTypeRegistryHolder:
    """Thread-safe event type registry singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get registry instance."""
        return cls._instance

    @classmethod
    def set(cls, registry: Any) -> None:
        """Set registry instance."""
        cls._instance = registry


class _CommandRegistryHolder:
    """Thread-safe command registry singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get registry instance."""
        return cls._instance

    @classmethod
    def set(cls, registry: Any) -> None:
        """Set registry instance."""
        cls._instance = registry


class _SecretManagerHolder:
    """Thread-safe secret manager singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get secret manager instance."""
        return cls._instance

    @classmethod
    def set(cls, manager: Any) -> None:
        """Set secret manager instance."""
        cls._instance = manager


class _ContainerHolder:
    """Thread-safe container singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get container instance."""
        return cls._instance

    @classmethod
    def set(cls, container: Any) -> None:
        """Set container instance."""
        cls._instance = container


class _ProtocolCacheHolder:
    """
    Thread-safe protocol cache singleton holder.

    Manages cached protocol services for logging infrastructure
    with TTL-based expiration.
    """

    _formatter: Any | None = None
    _output_handler: Any | None = None
    _timestamp: float = 0.0
    _ttl: float = 300  # 5 minutes TTL
    _lock = threading.Lock()

    @classmethod
    def get_formatter(cls) -> Any | None:
        """Get cached formatter."""
        return cls._formatter

    @classmethod
    def set_formatter(cls, formatter: Any) -> None:
        """Set cached formatter."""
        cls._formatter = formatter

    @classmethod
    def get_output_handler(cls) -> Any | None:
        """Get cached output handler."""
        return cls._output_handler

    @classmethod
    def set_output_handler(cls, handler: Any) -> None:
        """Set cached output handler."""
        cls._output_handler = handler

    @classmethod
    def get_timestamp(cls) -> float:
        """Get cache timestamp."""
        return cls._timestamp

    @classmethod
    def set_timestamp(cls, timestamp: float) -> None:
        """Set cache timestamp."""
        cls._timestamp = timestamp

    @classmethod
    def get_ttl(cls) -> float:
        """Get cache TTL."""
        return cls._ttl


class _LoggerCache:
    """Thread-safe logger cache holder."""

    _instance: Any = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> Any | None:
        """Get cached logger instance."""
        return cls._instance

    @classmethod
    def set(cls, logger: Any) -> None:
        """Set cached logger instance."""
        cls._instance = logger


class _SimpleFallbackLogger:
    """Simple fallback logger that just prints to stdout."""

    def emit(self, level: Any, message: str, correlation_id: Any) -> None:
        """Emit log message to stdout."""
        import sys

        # Import LogLevel here to avoid circular imports
        from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

        # ERROR and CRITICAL levels go to stderr, others to stdout
        is_error = level in (LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.FATAL)
        print(
            f"[{level.name}] {correlation_id}: {message}",
            file=sys.stderr if is_error else sys.stdout,
        )
