"""TypedDict for event type dictionary representation.

This module provides strongly-typed dictionary definitions for event types
used throughout the ONEX system for inter-service communication and discovery.
"""

from typing import TypedDict


class TypedDictEventType(TypedDict, total=False):
    """TypedDict for event type dictionary representation.

    Used in normalize_legacy_event_type when handling dict-based event types.

    Attributes:
        value: The event type value as a string
        event_type: Alternative field name for the event type
    """

    value: str
    event_type: str


__all__ = ["TypedDictEventType"]
