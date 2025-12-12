"""TypedDict for event metadata in lifecycle events."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictEventMetadata(TypedDict):
    """TypedDict for event metadata in lifecycle events."""

    event_type: str
    timestamp: str
    node_id: str
    correlation_id: NotRequired[str]


__all__ = ["TypedDictEventMetadata"]
