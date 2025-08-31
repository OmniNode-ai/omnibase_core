"""
Structured Logging for ONEX Core

Provides centralized structured logging with standardized formats.
"""

import json
import logging
from datetime import datetime
from typing import Any

from omnibase.protocols.types import LogLevel


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Emit a structured log event synchronously.

    Args:
        level: Log level from SPI LogLevel
        message: Log message
        context: Optional context dictionary
    """
    logger = logging.getLogger("omnibase")

    # Create structured log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
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

    logger.log(python_level, json.dumps(log_entry))
