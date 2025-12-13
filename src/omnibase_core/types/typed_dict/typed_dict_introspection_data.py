"""TypedDict for introspection data from event-driven nodes."""

from __future__ import annotations

from typing import TypedDict


class TypedDictIntrospectionData(TypedDict):
    """TypedDict for introspection data from event-driven nodes."""

    node_name: str
    node_id: str
    version: str
    capabilities: list[str]
    status: str
    event_types_handled: list[str]


__all__ = ["TypedDictIntrospectionData"]
