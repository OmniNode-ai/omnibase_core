"""TypedDict for computation output base summary.

Provides strongly-typed summary return values for computation output models,
replacing dict[str, Any] return types in get_summary() methods.
"""

from typing import TypedDict


class TypedDictComputationOutputSummary(TypedDict):
    """Summary of computation output base.

    Attributes:
        computation_type: Type of computation performed
        computed_values_count: Number of computed values
        metrics_count: Number of metrics recorded
        status_flags_count: Number of status flags set
        metadata_count: Number of metadata entries
    """

    computation_type: str
    computed_values_count: int
    metrics_count: int
    status_flags_count: int
    metadata_count: int


__all__ = ["TypedDictComputationOutputSummary"]
