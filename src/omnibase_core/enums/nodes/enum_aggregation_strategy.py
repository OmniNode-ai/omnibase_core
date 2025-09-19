"""
Aggregation strategy enum for node data processing.
"""

from enum import Enum


class EnumAggregationStrategy(str, Enum):
    """Supported aggregation strategies for node data processing."""

    SUM = "sum"
    AVERAGE = "average"
    MEAN = "mean"  # Alias for average
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    MEDIAN = "median"
    MODE = "mode"
    CONCAT = "concat"
    UNIQUE = "unique"
