"""
Typed structure for core data updates.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictCoreData(TypedDict, total=False):
    total_nodes: int
    active_nodes: int
    deprecated_nodes: int
    disabled_nodes: int


__all__ = ["TypedDictCoreData"]
