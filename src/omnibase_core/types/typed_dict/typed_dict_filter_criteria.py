"""TypedDict for discovery filter criteria (all fields optional)."""

from __future__ import annotations

from typing import TypedDict


class TypedDictFilterCriteria(TypedDict, total=False):
    """TypedDict for discovery filter criteria (all fields optional)."""

    capabilities: list[str]
    name_pattern: str
    node_type: str
    status: str


__all__ = ["TypedDictFilterCriteria"]
