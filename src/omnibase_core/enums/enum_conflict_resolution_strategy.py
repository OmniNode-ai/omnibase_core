"""
Conflict Resolution Strategy Enum.

Canonical enum for conflict resolution strategies used in KV synchronization
and distributed data management systems.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConflictResolutionStrategy(StrValueHelper, str, Enum):
    """Canonical conflict resolution strategies for ONEX distributed operations."""

    TIMESTAMP_WINS = "timestamp_wins"
    MANUAL = "manual"
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MERGE = "merge"
    LAST_WRITER_WINS = "last_writer_wins"


__all__ = ["EnumConflictResolutionStrategy"]
