"""Reduction type enumeration for data aggregation operations."""

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
