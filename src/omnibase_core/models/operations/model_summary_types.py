"""
Summary type definitions for computation output models.

Provides TypedDict definitions for strongly-typed summary return values,
replacing dict[str, Any] return types in get_*_summary() methods.
"""

from typing import TypedDict


class ComputationOutputSummaryDict(TypedDict):
    """Summary of computation output base."""

    computation_type: str
    computed_values_count: int
    metrics_count: int
    status_flags_count: int
    metadata_count: int


class NumericPrecisionSummaryDict(TypedDict):
    """Summary of numeric computation precision."""

    precision_achieved: int
    result_count: int
    has_errors: bool
    convergence_status: bool


class BinaryComputationSummaryDict(TypedDict):
    """Summary of binary computation output."""

    result_count: int
    total_size_bytes: int
    checksums_verified: bool
    compression_ratio: float
    data_integrity_status: str
    is_data_intact: bool
    compression_efficiency: str


class TextComputationSummaryDict(TypedDict):
    """Summary of text computation output."""

    language_detected: str
    result_count: int
    average_confidence: float
    has_warnings: bool
    warning_count: int


class StructuredComputationSummaryDict(TypedDict):
    """Summary of structured computation output."""

    result_count: int
    schema_valid: bool
    validation_status: str
    nested_depth: int
    total_transformations: int
    complexity_score: float


class ComputationOutputDataSummaryDict(TypedDict):
    """Summary of full computation output data."""

    computation_type: str
    computed_values_count: int
    metrics_count: int
    status_flags_count: int
    metadata_count: int
    processing_info_count: int


__all__ = [
    "BinaryComputationSummaryDict",
    "ComputationOutputDataSummaryDict",
    "ComputationOutputSummaryDict",
    "NumericPrecisionSummaryDict",
    "StructuredComputationSummaryDict",
    "TextComputationSummaryDict",
]
