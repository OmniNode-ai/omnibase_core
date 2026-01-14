#!/usr/bin/env python3
"""
Cache eviction policy enumeration for ONEX caching systems.

Defines eviction strategies for cache management.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCacheEvictionPolicy(StrValueHelper, str, Enum):
    """
    Cache eviction policy enumeration for ONEX caching systems.

    Defines the strategies for removing entries when cache reaches capacity.
    """

    LRU = "lru"  # Least Recently Used - evicts oldest accessed entry
    LFU = "lfu"  # Least Frequently Used - evicts least accessed entry
    FIFO = "fifo"  # First In First Out - evicts oldest inserted entry


__all__ = ["EnumCacheEvictionPolicy"]
