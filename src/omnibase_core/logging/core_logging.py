"""
Simple, clean ONEX logging - just emit_log_event(level, message).

This module provides the simplest possible logging interface:
- emit_log_event(level, message) - that's it!
- Automatic correlation ID management
- Registry-based protocol resolution
- Fire-and-forget async performance
"""

import asyncio
import threading
from uuid import UUID, uuid4

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

# Thread-local correlation ID context
_context = threading.local()

# Cached logger instance from registry
_cached_logger = None
_cache_lock = threading.Lock()


def emit_log_event(level: LogLevel, message: str) -> None:
    """
    The only logging function you need - simple and clean.
    Registry-resolved logger with automatic correlation ID management.

    Args:
        level: Log level (LogLevel.INFO, LogLevel.ERROR, etc.)
        message: Log message
    """
    # Get logger from registry (cached for performance)
    logger = _get_registry_logger()

    # Get or create correlation ID automatically
    correlation_id = _get_correlation_id()

    # Use the registry-resolved logger
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_async_emit_via_logger(logger, level, message, correlation_id))
    except RuntimeError:
        # No event loop, use sync fallback
        logger.emit(level, message, correlation_id)


def set_correlation_id(correlation_id: UUID) -> None:
    """Set correlation ID for this thread context."""
    _context.correlation_id = correlation_id


def get_correlation_id() -> UUID | None:
    """Get current correlation ID."""
    return getattr(_context, "correlation_id", None)


# Simple fallback logger for when container/registry is unavailable
class _SimpleFallbackLogger:
    """Simple fallback logger that just prints to stdout."""

    def emit(self, level: LogLevel, message: str, correlation_id: UUID) -> None:
        """Emit log message to stdout."""
        import sys

        print(
            f"[{level.name}] {correlation_id}: {message}",
            file=sys.stdout if level.value < 40 else sys.stderr,
        )


# Internal implementation
def _get_correlation_id() -> UUID:
    """Get or create correlation ID."""
    correlation_id = getattr(_context, "correlation_id", None)
    if correlation_id is None:
        _context.correlation_id = uuid4()
        correlation_id = _context.correlation_id
    return correlation_id


def _get_registry_logger():
    """Get logger from registry with caching for performance."""
    global _cached_logger

    # Double-checked locking pattern for thread safety
    if _cached_logger is None:
        with _cache_lock:
            if _cached_logger is None:
                try:
                    # Try to get logger from container
                    from omnibase_core.container import EnhancedContainer

                    container = EnhancedContainer()
                    _cached_logger = container.get_service("Logger")

                    if _cached_logger is None:
                        # Fallback to simple logger
                        _cached_logger = _SimpleFallbackLogger()

                except Exception:
                    # Final fallback to simple logger
                    _cached_logger = _SimpleFallbackLogger()

    return _cached_logger


async def _async_emit_via_logger(
    logger,
    level: LogLevel,
    message: str,
    correlation_id: UUID,
) -> None:
    """Async fire-and-forget logging via registry-resolved logger."""
    try:
        # Use the registry-resolved logger
        logger.emit(level, message, correlation_id)
    except Exception:
        # Fallback to simple print if logger fails
        pass
