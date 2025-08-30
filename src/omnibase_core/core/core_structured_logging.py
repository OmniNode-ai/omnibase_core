"""
Structured Logging for ONEX Core

Provides centralized structured logging with standardized formats.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from omnibase_core.enums import EnumLogLevel as LogLevelEnum


def emit_log_event_sync(
    level: LogLevelEnum, message: str, context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Emit a structured log event synchronously.

    Args:
        level: Log level from LogLevelEnum
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

    # Map LogLevelEnum to Python logging levels
    python_level = {
        LogLevelEnum.DEBUG: logging.DEBUG,
        LogLevelEnum.INFO: logging.INFO,
        LogLevelEnum.WARNING: logging.WARNING,
        LogLevelEnum.ERROR: logging.ERROR,
        LogLevelEnum.CRITICAL: logging.CRITICAL,
    }.get(level, logging.INFO)

    logger.log(python_level, json.dumps(log_entry))
