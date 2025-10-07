import uuid
from datetime import datetime
from typing import Callable, Dict, TypeVar

"""
Core emit_log_event utility for ONEX structured logging.

This module provides the main entry point for all ONEX logging, routing
events through the logger node with smart formatting and correlation tracking.

All internal ONEX logging should use emit_log_event() instead of print() or
Python's logging module to maintain architectural purity and centralized processing.
"""

import inspect
import os
from collections.abc import Callable as CallableABC
from datetime import UTC, datetime
from typing import Any, Callable, Dict, TypeVar
from uuid import UUID, uuid4

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_log_context import ModelLogContext

# Type aliases for logging infrastructure (BOUNDARY_LAYER_EXCEPTION)
# These types support logging resilience by allowing flexible identifiers
# when strict UUID context is unavailable (e.g., during bootstrap or error handling)
LogNodeIdentifier = UUID | str
# LogDataValue uses Any for boundary layer flexibility - logging infrastructure
# needs to accept various types while sanitization ensures JSON compatibility
LogDataValue = Any
F = TypeVar("F", bound=Callable[..., Any])


def emit_log_event(
    level: LogLevel,
    event_type: str,
    message: str,
    correlation_id: UUID,
    node_id: LogNodeIdentifier | None = None,
    data: dict[str, LogDataValue | None] | None = None,
    event_bus: Any | None = None,
) -> None:
    """
    Emit a structured log event through the logger node.

    This is the main entry point for all ONEX logging. Routes events through
    the logger node for centralized processing with smart formatting.

    Args:
        level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        event_type: Type of event (function_entry, node_execution_start, etc.)
        message: Primary log message
        correlation_id: Correlation ID for tracing (required - callers must provide)
        node_id: Node ID for context (auto-detected if not provided).
            BOUNDARY_LAYER_EXCEPTION: Accepts UUID | str | None for logging
            infrastructure resilience. String fallbacks used when UUID context
            unavailable (e.g., "unknown", module names for debugging).
        data: Additional structured data
        event_bus: Event bus for routing (uses default if not provided)
    """
    # Auto-detect node ID from calling context if not provided
    if node_id is None:
        node_id = _detect_node_id_from_context()

    # Create log context from calling frame
    context = _create_log_context_from_frame()

    # Get or create event bus
    if event_bus is None:
        event_bus = _get_default_event_bus()

    # Sanitize sensitive data before routing
    sanitized_message = _sanitize_sensitive_data(message)
    sanitized_data = _sanitize_data_dict(data or {})

    # Route through logger node
    _route_to_logger_node(
        level=level,
        event_type=event_type,
        message=sanitized_message,
        node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
        correlation_id=correlation_id,
        context=context,
        data=sanitized_data,
        event_bus=event_bus,
    )


def emit_log_event_with_new_correlation(
    level: LogLevel,
    event_type: str,
    message: str,
    node_id: LogNodeIdentifier | None = None,
    data: dict[str, LogDataValue | None] | None = None,
    event_bus: Any | None = None,
) -> UUID:
    """
    Emit a structured log event with a new correlation ID.

    This is a convenience function for cases where a new correlation ID should be generated.
    Returns the generated correlation ID for use in subsequent related operations.

    Args:
        level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        event_type: Type of event (function_entry, node_execution_start, etc.)
        message: Primary log message
        node_id: Node ID for context (auto-detected if not provided)
        data: Additional structured data
        event_bus: Event bus for routing (uses default if not provided)

    Returns:
        UUID: The generated correlation ID
    """
    correlation_id = uuid4()
    emit_log_event(
        level=level,
        event_type=event_type,
        message=message,
        correlation_id=correlation_id,
        node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
        data=data,
        event_bus=event_bus,
    )
    return correlation_id


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    correlation_id: UUID,
    event_type: str = "generic",
    node_id: LogNodeIdentifier | None = None,
    data: dict[str, LogDataValue | None] | None = None,
    event_bus: Any | None = None,
) -> None:
    """
    Synchronous version of emit_log_event for current standards.

    Args:
        level: Log level
        message: Log message
        correlation_id: Correlation ID (required)
        event_type: Event type
        node_id: Node ID
        data: Additional data
        event_bus: Event bus
    """
    emit_log_event(
        level=level,
        event_type=event_type,
        message=message,
        correlation_id=correlation_id,
        node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
        data=data,
        event_bus=event_bus,
    )


async def emit_log_event_async(
    level: LogLevel,
    message: str,
    correlation_id: UUID,
    event_type: str = "generic",
    node_id: LogNodeIdentifier | None = None,
    data: dict[str, LogDataValue | None] | None = None,
    event_bus: Any | None = None,
) -> None:
    """
    Asynchronous version of emit_log_event.

    Args:
        level: Log level
        message: Log message
        correlation_id: Correlation ID (required)
        event_type: Event type
        node_id: Node ID
        data: Additional data
        event_bus: Event bus
    """
    # For now, delegate to sync version
    # [AI_PROMPT] Implement true async routing when logger node supports it
    # This requires async protocol interfaces for Any and logger node routing
    # Implementation should preserve correlation IDs and maintain protocol purity
    emit_log_event(
        level=level,
        event_type=event_type,
        message=message,
        correlation_id=correlation_id,
        node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
        data=data,
        event_bus=event_bus,
    )


def trace_function_lifecycle(func: F) -> F:
    """
    Decorator to automatically log function entry/exit with TRACE level.

    Usage:
        @trace_function_lifecycle
        def my_function(arg1, arg2):
            return result
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        function_name = func.__name__
        module_name = func.__module__
        correlation_id = uuid4()

        # Log function entry
        emit_log_event(
            level=LogLevel.TRACE,
            event_type="function_entry",
            message=f"Entering {function_name}",
            correlation_id=correlation_id,
            data={
                "function": function_name,
                "module": module_name,
                "args_count": len(args),
                "kwargs_count": len(kwargs),
            },
        )

        start_time = datetime.now(UTC)
        try:
            result = func(*args, **kwargs)

            # Log successful exit
            end_time = datetime.now(UTC)
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            emit_log_event(
                level=LogLevel.TRACE,
                event_type="function_exit",
                message=f"Exiting {function_name}",
                correlation_id=correlation_id,
                data={
                    "function": function_name,
                    "module": module_name,
                    "execution_time_ms": execution_time_ms,
                    "success": True,
                },
            )

            return result

        except Exception as e:
            # Log exception exit
            end_time = datetime.now(UTC)
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            emit_log_event(
                level=LogLevel.TRACE,
                event_type="function_exception",
                message=f"Exception in {function_name}: {e!s}",
                correlation_id=correlation_id,
                data={
                    "function": function_name,
                    "module": module_name,
                    "execution_time_ms": execution_time_ms,
                    "success": False,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                },
            )

            raise

    return wrapper  # type: ignore[return-value]


class log_code_block:
    """
    Context manager for logging code block execution.

    Usage:
        with log_code_block("processing_data", correlation_id=some_uuid):
            # code block
            pass
    """

    def __init__(
        self,
        block_name: str,
        correlation_id: UUID,
        level: LogLevel = LogLevel.DEBUG,
        data: dict[str, LogDataValue | None] | None = None,
    ) -> None:
        self.block_name = block_name
        self.correlation_id = correlation_id
        self.level = level
        self.data = data or {}
        self.start_time: datetime | None = None

    def __enter__(self) -> "log_code_block":
        self.start_time = datetime.now(UTC)

        emit_log_event(
            level=self.level,
            event_type="code_block_entry",
            message=f"Entering code block: {self.block_name}",
            correlation_id=self.correlation_id,
            data={
                "block_name": self.block_name,
                **self.data,
            },
        )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            end_time = datetime.now(UTC)
            execution_time_ms = (end_time - self.start_time).total_seconds() * 1000
        else:
            execution_time_ms = 0

        if exc_type is None:
            # Successful completion
            emit_log_event(
                level=self.level,
                event_type="code_block_exit",
                message=f"Exiting code block: {self.block_name}",
                correlation_id=self.correlation_id,
                data={
                    "block_name": self.block_name,
                    "execution_time_ms": execution_time_ms,
                    "success": True,
                    **self.data,
                },
            )
        else:
            # Exception occurred
            emit_log_event(
                level=LogLevel.ERROR,
                event_type="code_block_exception",
                message=f"Exception in code block {self.block_name}: {exc_val!s}",
                correlation_id=self.correlation_id,
                data={
                    "block_name": self.block_name,
                    "execution_time_ms": execution_time_ms,
                    "success": False,
                    "exception_type": exc_type.__name__ if exc_type else None,
                    "exception_message": str(exc_val) if exc_val else None,
                    **self.data,
                },
            )


def log_performance_metrics(threshold_ms: int = 1000) -> Callable[[F], F]:
    """
    Decorator to log performance metrics for functions.

    Args:
        threshold_ms: Log warning if execution exceeds this threshold

    Usage:
        @log_performance_metrics(threshold_ms=500)
        def slow_function():
            pass
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            function_name = func.__name__
            correlation_id = uuid4()

            start_time = datetime.now(UTC)
            result = func(*args, **kwargs)
            end_time = datetime.now(UTC)

            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            if execution_time_ms > threshold_ms:
                emit_log_event(
                    level=LogLevel.WARNING,
                    event_type="performance_threshold_exceeded",
                    message=f"Function {function_name} exceeded performance threshold",
                    correlation_id=correlation_id,
                    data={
                        "function": function_name,
                        "execution_time_ms": execution_time_ms,
                        "threshold_ms": threshold_ms,
                        "operation_name": function_name,
                    },
                )
            else:
                emit_log_event(
                    level=LogLevel.DEBUG,
                    event_type="performance_metrics",
                    message=f"Function {function_name} performance metrics",
                    correlation_id=correlation_id,
                    data={
                        "function": function_name,
                        "execution_time_ms": execution_time_ms,
                        "threshold_ms": threshold_ms,
                        "operation_name": function_name,
                    },
                )

            return result

        return wrapper  # type: ignore[return-value]

    return decorator


# Private helper functions

import threading

# Global cache for protocol services to reduce lookup overhead
import time

_cached_formatter = None
_cached_output_handler = None
_cache_timestamp = 0.0
_cache_ttl = 300  # 5 minutes TTL
_cache_lock = threading.Lock()  # Initialize lock at module level

# Sensitive data patterns for sanitization
import re

_SENSITIVE_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b"), "[REDACTED_TOKEN]"),  # Base64 tokens
    (
        re.compile(r'\bpassword["\']?\s*[:=]\s*["\']?[^,}\s]+["}]?', re.IGNORECASE),
        "password=[REDACTED]",
    ),  # Passwords
    (
        re.compile(r'\bapi[_-]?key["\']?\s*[:=]\s*["\']?[^,}\s]+["}]?', re.IGNORECASE),
        "api_key=[REDACTED]",
    ),  # API keys
    (
        re.compile(r'\bsecret["\']?\s*[:=]\s*["\']?[^,}\s]+["}]?', re.IGNORECASE),
        "secret=[REDACTED]",
    ),  # Secrets
    (
        re.compile(
            r'\baccess[_-]?token["\']?\s*[:=]\s*["\']?[^,}\s]+["}]?',
            re.IGNORECASE,
        ),
        "access_token=[REDACTED]",
    ),  # Access tokens
]


def _sanitize_sensitive_data(text: str) -> str:
    """
    Sanitize sensitive data patterns from log messages.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text with sensitive patterns redacted
    """
    if not isinstance(text, str):
        return text  # type: ignore[unreachable, return-value]

    sanitized = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def _sanitize_data_dict(
    data: dict[str, LogDataValue | None],
) -> dict[str, LogDataValue | None]:
    """
    Sanitize sensitive data in a data dict[str, Any]ionary and ensure JSON compatibility.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dict[str, Any]ionary with JSON-compatible values
    """
    if not isinstance(data, dict):
        return data  # type: ignore[unreachable, return-value]

    sanitized: dict[str, Any | None] = {}
    for key, value in data.items():
        # Sanitize key names that might contain sensitive info
        sanitized_key = _sanitize_sensitive_data(str(key))

        # Validate and sanitize values to ensure JSON compatibility
        sanitized_value: Any | None
        if isinstance(value, str):
            sanitized_value = _sanitize_sensitive_data(value)
        elif isinstance(value, bool):  # Check bool first (bool is subclass of int)
            sanitized_value = value
        elif isinstance(value, int):
            sanitized_value = value
        elif isinstance(value, float):
            sanitized_value = value
        elif value is None:
            sanitized_value = value
        else:
            # Convert non-JSON-compatible types to string representation
            sanitized_value = _sanitize_sensitive_data(str(value))

        sanitized[sanitized_key] = sanitized_value

    return sanitized


def _get_or_generate_correlation_id() -> str:
    """Get correlation ID from context or generate a new one using UUID service."""
    # Try to get from thread-local storage or environment
    correlation_id = os.getenv("ONEX_CORRELATION_ID")
    if correlation_id:
        return correlation_id

    # UUID ModelArchitecture: Use centralized UUID service for consistent generation
    return str(uuid4())[:8]


def _detect_node_id_from_context() -> LogNodeIdentifier:
    """Detect node ID from calling context with limited stack depth.

    BOUNDARY_LAYER_EXCEPTION: Returns UUID | str to support logging infrastructure
    resilience. Returns UUID from node instances when available, falls back to
    string identifiers (class/module names) for debugging when UUID unavailable.

    Returns:
        UUID if found from a node instance, or str fallback (class name or module name)
    """
    frame = inspect.currentframe()
    original_frame = frame
    max_depth = 10  # Limit stack walking to prevent performance issues
    depth = 0

    try:
        # Walk up the stack to find a node context with depth limit
        while frame and depth < max_depth:
            frame = frame.f_back
            depth += 1

            if frame and "self" in frame.f_locals:
                obj = frame.f_locals["self"]
                if hasattr(obj, "node_id"):
                    return obj.node_id
                if (
                    hasattr(obj, "__class__")
                    and "node" in obj.__class__.__name__.lower()
                ):
                    return obj.__class__.__name__

        # Fallback to module name
        caller_frame = inspect.currentframe()
        try:
            if caller_frame and caller_frame.f_back and caller_frame.f_back.f_back:
                caller_frame = caller_frame.f_back.f_back
                module_name = caller_frame.f_globals.get("__name__", "unknown")
                return module_name.split(".")[-1]
        finally:
            del caller_frame

        return "unknown"
    finally:
        # Clean up all frame references
        del frame
        del original_frame


def _create_log_context_from_frame() -> ModelLogContext:
    """Create log context from the calling frame."""
    frame = inspect.currentframe()

    # Walk up the stack to get the actual caller
    if frame and frame.f_back and frame.f_back.f_back:
        frame = frame.f_back.f_back
        node_id_raw = _detect_node_id_from_context()
        return ModelLogContext(
            calling_function=frame.f_code.co_name,
            calling_module=frame.f_globals.get("__name__", "unknown"),
            calling_line=frame.f_lineno,
            timestamp=datetime.now(UTC).isoformat(),
            node_id=UUID(node_id_raw) if isinstance(node_id_raw, str) else node_id_raw,
        )
    return ModelLogContext(
        calling_function="unknown",
        calling_module="unknown",
        calling_line=0,
        timestamp=datetime.now(UTC).isoformat(),
        node_id=UUID("00000000-0000-0000-0000-000000000000"),
    )


def _get_default_event_bus() -> Any | None:
    """Get the default event bus for logging using protocol-based discovery."""
    try:
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        from omnibase_core.nodes.node_runtime.protocols.protocol_event_bus_factory import (
            AnyFactory,
        )

        # Try to get container and event bus factory
        container = ModelONEXContainer()
        event_bus_factory = container.get_service(AnyFactory)

        if event_bus_factory:
            return event_bus_factory.get_event_bus()

        return None
    except Exception:
        # fallback-ok: logger unavailable during bootstrap
        return None


def _route_to_logger_node(
    level: LogLevel,
    event_type: str,
    message: str,
    node_id: LogNodeIdentifier,
    correlation_id: UUID,
    context: ModelLogContext,
    data: dict[str, LogDataValue | None],
    event_bus: Any | None,
) -> None:
    """
    Route log event to logger node for processing using protocol-based discovery.

    This function handles the actual routing of log events to the logger node
    with smart formatting and output handling via protocol abstractions.

    Args:
        node_id: BOUNDARY_LAYER_EXCEPTION - accepts UUID | str for logging
            infrastructure resilience (see emit_log_event for rationale).
    """
    global _cached_formatter, _cached_output_handler, _cache_timestamp, _cache_ttl, _cache_lock

    try:
        # Check cache with TTL validation
        current_time = time.time()
        cache_expired = (current_time - _cache_timestamp) > _cache_ttl

        formatter = _cached_formatter
        output_handler = _cached_output_handler

        # If not cached or cache expired, perform lookup with locking
        if formatter is None or output_handler is None or cache_expired:  # type: ignore[unreachable]
            with _cache_lock:
                # Double-check after acquiring lock
                current_time = time.time()
                cache_expired = (current_time - _cache_timestamp) > _cache_ttl

                # Re-check after lock acquisition (may have changed)
                if _cached_formatter is None or _cached_output_handler is None or cache_expired:  # type: ignore[unreachable]
                    from omnibase_core.models.container.model_onex_container import (
                        ModelONEXContainer,
                    )
                    from omnibase_core.nodes.node_logger.protocols.protocol_context_aware_output_handler import (
                        ProtocolContextAwareOutputHandler,
                    )
                    from omnibase_core.nodes.node_logger.protocols.protocol_smart_log_formatter import (
                        ProtocolSmartLogFormatter,
                    )

                    # Try to get logger components from container
                    try:
                        container = ModelONEXContainer()
                        _cached_formatter = container.get_service(
                            ProtocolSmartLogFormatter,
                        )
                        _cached_output_handler = container.get_service(
                            ProtocolContextAwareOutputHandler,
                        )
                        _cache_timestamp = current_time
                    except Exception:
                        # If container fails, use None to trigger fallback logging
                        _cached_formatter = None
                        _cached_output_handler = None
                        _cache_timestamp = current_time

                formatter = _cached_formatter
                output_handler = _cached_output_handler

        if formatter and output_handler:
            # Format the log event using protocol
            formatted_log = formatter.format_log_event(
                level=level,
                event_type=event_type,
                message=message,
                context=context,
                data=data,
                correlation_id=str(correlation_id),
            )

            # Output the formatted log using protocol
            output_handler.output_log_entry(formatted_log, level.name)
        else:
            # Fallback to simple output if protocol services unavailable
            pass

    except Exception:
        # Fallback to simple output if logger node routing fails
        pass
