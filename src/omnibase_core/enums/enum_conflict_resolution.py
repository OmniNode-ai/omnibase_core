"""Conflict resolution strategy enumeration for data reduction."""

from enum import Enum, unique


@unique
class EnumConflictResolution(Enum):
    """Strategies for resolving conflicts during reduction."""

    FIRST_WINS = "first_wins"  # Keep first encountered value
    LAST_WINS = "last_wins"  # Keep last encountered value
    MERGE = "merge"  # Attempt to merge values
    ERROR = "error"  # Raise error on conflict
    CUSTOM = "custom"  # Use custom resolution function
