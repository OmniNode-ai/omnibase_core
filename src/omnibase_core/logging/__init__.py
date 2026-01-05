"""Logging module.

This module contains structured logging, event emission, and bootstrap logging.
"""

from omnibase_core.logging.logging_emit import emit_log_event
from omnibase_core.logging.logging_structured import emit_log_event_sync

__all__ = [
    "emit_log_event_sync",
    "emit_log_event",
]
