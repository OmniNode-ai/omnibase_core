"""TypedDict for structured computation output summary.

Provides strongly-typed summary return values for structured computation output,
replacing dict[str, Any] return types in get_structured_summary() methods.
"""

from typing import TypedDict


class TypedDictStructuredComputationSummary(TypedDict):
    """Summary of structured computation output.

    Attributes:
        result_count: Number of structured results
        schema_valid: Whether schema validation passed
        validation_status: Status of schema validation
        nested_depth: Maximum nesting depth in structure
        total_transformations: Total number of transformations applied
        complexity_score: Complexity score of the structure
    """

    result_count: int
    schema_valid: bool
    validation_status: str
    nested_depth: int
    total_transformations: int
    complexity_score: float


__all__ = ["TypedDictStructuredComputationSummary"]
