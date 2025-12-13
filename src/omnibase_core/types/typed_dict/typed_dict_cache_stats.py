"""TypedDict for cache statistics from MixinCaching."""

from __future__ import annotations

from typing import TypedDict


class TypedDictCacheStats(TypedDict):
    """TypedDict for cache statistics from MixinCaching."""

    enabled: bool
    entries: int
    keys: list[str]


__all__ = ["TypedDictCacheStats"]
