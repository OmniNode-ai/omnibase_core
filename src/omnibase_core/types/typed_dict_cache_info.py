"""
TypedDict for cache information.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictCacheInfo(TypedDict):
    cache_name: str
    cache_size: int
    max_size: int
    hit_count: int
    miss_count: int
    eviction_count: int
    hit_rate: float


__all__ = ["TypedDictCacheInfo"]
