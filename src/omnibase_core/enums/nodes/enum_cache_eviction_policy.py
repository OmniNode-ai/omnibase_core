"""
Cache eviction policy enum for caching configurations.
"""

from enum import Enum


class EnumCacheEvictionPolicy(str, Enum):
    """Supported cache eviction policies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    RANDOM = "random"
    TTL = "ttl"  # Time To Live based
    SIZE_BASED = "size_based"
