"""
Structured Logging for ONEX Core

Provides centralized structured logging with standardized formats.
"""

import json
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

try:
    from omnibase_spi.protocols.types.core_types import ProtocolLogContext
except ImportError:
    # Fallback for when omnibase-spi is not available
    from typing import Protocol

    class ProtocolLogContext(Protocol):
        def to_dict(self) -> dict[str, Any]: ...


class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models and log contexts."""

    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if hasattr(obj, "to_dict"):  # Handle ProtocolLogContext
            return obj.to_dict()
        return super().default(obj)


def emit_log_event_sync(
    level: LogLevel,
    message: str,
    context: dict[str, Any] | ProtocolLogContext | BaseModel | None = None,
) -> None:
    """
    Emit a structured log event synchronously.

    Args:
        level: Log level from SPI LogLevel
        message: Log message
        context: Optional context dictionary, log context protocol, or Pydantic model
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

    logger.log(python_level, json.dumps(log_entry, cls=PydanticJSONEncoder))
