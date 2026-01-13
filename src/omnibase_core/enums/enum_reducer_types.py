"""
Reducer Type Enums for 4-Node Architecture.

Defines enums for reduction operations, conflict resolution strategies,
and streaming processing modes.
"""

from enum import Enum, unique


@unique
class EnumReductionType(Enum):
    """Types of reduction operations supported."""

    FOLD = "fold"  # Reduce collection to single value
    ACCUMULATE = "accumulate"  # Build up result incrementally
    MERGE = "merge"  # Combine multiple datasets
    AGGREGATE = "aggregate"  # Statistical aggregation
    NORMALIZE = "normalize"  # Score normalization and ranking
    DEDUPLICATE = "deduplicate"  # Remove duplicates
    SORT = "sort"  # Sort and rank operations
    FILTER = "filter"  # Filter with conditions
    GROUP = "group"  # Group by criteria
    TRANSFORM = "transform"  # Data transformation


@unique
class EnumConflictResolution(Enum):
    """Strategies for resolving conflicts during reduction."""

    FIRST_WINS = "first_wins"  # Keep first encountered value
    LAST_WINS = "last_wins"  # Keep last encountered value
    MERGE = "merge"  # Attempt to merge values
    ERROR = "error"  # Raise error on conflict
    CUSTOM = "custom"  # Use custom resolution function


@unique
class EnumStreamingMode(Enum):
    """Streaming processing modes."""

    BATCH = "batch"  # Process all data at once
    INCREMENTAL = "incremental"  # Process data incrementally
    WINDOWED = "windowed"  # Process in time windows
    REAL_TIME = "real_time"  # Process as data arrives
