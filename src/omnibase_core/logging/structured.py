from datetime import datetime

"""
Structured Logging for ONEX Core

Provides centralized structured logging with standardized formats.
"""

import json
import logging
from datetime import UTC
from typing import Any

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.pydantic_json_encoder import PydanticJSONEncoder


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
        "level": level.value,
        "message": message,
        "context": context or {},
    }

    # Map SPI LogLevel to Python logging levels
    python_level = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
    }.get(level, logging.INFO)

    logger.log(python_level, json.dumps(log_entry, cls=PydanticJSONEncoder))
