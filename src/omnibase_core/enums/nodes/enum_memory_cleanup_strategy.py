"""
Memory cleanup strategy enum for REDUCER node configurations.
"""

from enum import Enum


class EnumMemoryCleanupStrategy(str, Enum):
    """Supported memory cleanup strategies for REDUCER nodes."""

    LRU = "lru"  # Least Recently Used
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    RANDOM = "random"
    SIZE_BASED = "size_based"
    AGE_BASED = "age_based"
    PRIORITY_BASED = "priority_based"
