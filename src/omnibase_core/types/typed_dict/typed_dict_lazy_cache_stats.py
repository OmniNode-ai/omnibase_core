"""TypedDict for lazy evaluation cache statistics."""

from __future__ import annotations

from typing import TypedDict


class TypedDictLazyCacheStats(TypedDict):
    """TypedDict for lazy evaluation cache statistics."""

    total_entries: int
    computed_entries: int
    pending_entries: int
    cache_hit_ratio: float
    memory_efficiency: str


__all__ = ["TypedDictLazyCacheStats"]
