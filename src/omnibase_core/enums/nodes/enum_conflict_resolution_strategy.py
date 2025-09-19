"""
Conflict resolution strategy enum for REDUCER node configurations.
"""

from enum import Enum


class EnumConflictResolutionStrategy(str, Enum):
    """Supported conflict resolution strategies for REDUCER nodes."""

    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    PRIORITY_BASED = "priority_based"
    TIMESTAMP_BASED = "timestamp_based"
    VERSION_BASED = "version_based"
    MANUAL_RESOLUTION = "manual_resolution"
    CONFLICT_FREE = "conflict_free"
