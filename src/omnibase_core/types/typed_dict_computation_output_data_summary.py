"""TypedDict for full computation output data summary.

Provides strongly-typed summary return values for computation output data,
replacing dict[str, Any] return types in get_data_summary() methods.
"""

from typing import TypedDict


class TypedDictComputationOutputDataSummary(TypedDict):
    """Summary of full computation output data.

    Attributes:
        computation_type: Type of computation performed
        computed_values_count: Number of computed values
        metrics_count: Number of metrics recorded
        status_flags_count: Number of status flags set
        metadata_count: Number of metadata entries
        processing_info_count: Number of processing info entries
    """

    computation_type: str
    computed_values_count: int
    metrics_count: int
    status_flags_count: int
    metadata_count: int
    processing_info_count: int


__all__ = ["TypedDictComputationOutputDataSummary"]
