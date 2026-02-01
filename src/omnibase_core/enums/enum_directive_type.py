"""
Runtime directive type enumeration.

This enum defines the types of internal runtime directives that are:
- NEVER published to event bus
- NEVER returned from handlers
- NOT part of ModelHandlerOutput

These are produced by runtime after interpreting intents or events.
Used for execution mechanics (scheduling, retries, delays).
"""

from enum import StrEnum, unique

__all__ = ["EnumDirectiveType"]


@unique
class EnumDirectiveType(StrEnum):
    """Runtime directive types (internal-only)."""

    SCHEDULE_EFFECT = "schedule_effect"
    ENQUEUE_HANDLER = "enqueue_handler"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    DELAY_UNTIL = "delay_until"
    CANCEL_EXECUTION = "cancel_execution"
