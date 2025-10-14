"""
Structured Logging for ONEX Core

Provides centralized structured logging with standardized formats.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

try:
    from omnibase_spi.protocols.types.core_types import (
        ProtocolLogContext,  # type: ignore[attr-defined]
    )
except ImportError:
    # Fallback for when omnibase_spi is not available
    from typing import Protocol

    class ProtocolLogContext(Protocol):  # type: ignore[no-redef]
        def to_dict(self) -> dict[str, Any]: ...


class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models, UUIDs, and log contexts."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "to_dict"):  # Handle ProtocolLogContext
            return obj.to_dict()
        return super().default(obj)


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
        context: Optional context (dict, log context protocol, or Pydantic model).
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
