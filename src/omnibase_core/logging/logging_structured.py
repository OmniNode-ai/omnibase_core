"""Structured logging for ONEX core.

Provides centralized structured logging with standardized JSON formats
using Python's logging module and custom Pydantic-aware JSON encoding.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_pydantic_encoder import PydanticJSONEncoder


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    context: Any = None,
) -> None:
    """
    Emit a structured log event synchronously.

    Args:
        level: Log level from SPI LogLevel
        message: Log message
        context: Optional context (dict[str, Any], log context protocol, or Pydantic model).
            BOUNDARY_LAYER_EXCEPTION: Uses Any for flexible input handling.
            Internally validated and converted to JSON-compatible format.
    """
    logger = logging.getLogger("omnibase")

    # Create structured log entry
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.value.lower(),
        "message": message,
        "context": context or {},
    }

    # Map SPI LogLevel to Python logging levels
    level_mapping = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
        LogLevel.FATAL: logging.CRITICAL,
    }

    python_level = level_mapping.get(level)
    if python_level is None:
        # fallback-ok: use INFO for unknown log levels but warn about configuration
        logger.warning(
            "Unknown log level %r, defaulting to INFO. "
            "Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL",
            level,
        )
        python_level = logging.INFO

    logger.log(python_level, json.dumps(log_entry, cls=PydanticJSONEncoder))
