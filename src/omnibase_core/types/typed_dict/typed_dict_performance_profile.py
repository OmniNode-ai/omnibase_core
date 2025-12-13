"""TypedDict for performance profile from MixinNodeIntrospection."""

from __future__ import annotations

from typing import TypedDict


class TypedDictPerformanceProfile(TypedDict):
    """TypedDict for performance profile from MixinNodeIntrospection."""

    typical_execution_time: str
    memory_usage: str
    cpu_intensive: bool


__all__ = ["TypedDictPerformanceProfile"]
