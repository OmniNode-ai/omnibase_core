from __future__ import annotations

"""
TypedDict for cache information.
"""

from typing import TypedDict


class TypedDictCacheInfo(TypedDict):
    """TypedDict for cache information."""

    cache_name: str
    cache_size: int
    max_size: int
    hit_count: int
    miss_count: int
    eviction_count: int
    hit_rate: float


__all__ = ["TypedDictCacheInfo"]
