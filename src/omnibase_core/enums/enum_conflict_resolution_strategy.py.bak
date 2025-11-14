"""
Conflict Resolution Strategy Enum.

Canonical enum for conflict resolution strategies used in KV synchronization
and distributed data management systems.
"""

from enum import Enum


class EnumConflictResolutionStrategy(str, Enum):
    """Canonical conflict resolution strategies for ONEX distributed operations."""

    TIMESTAMP_WINS = "timestamp_wins"
    MANUAL = "manual"
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MERGE = "merge"
    LAST_WRITER_WINS = "last_writer_wins"
