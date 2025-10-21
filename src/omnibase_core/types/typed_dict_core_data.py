from __future__ import annotations

from typing import TypedDict

"""
Typed structure for core data updates.
"""


class TypedDictCoreData(TypedDict, total=False):
    """Typed structure for core data updates."""

    total_nodes: int
    active_nodes: int
    deprecated_nodes: int
    disabled_nodes: int


__all__ = ["TypedDictCoreData"]
