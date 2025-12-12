"""TypedDict for numeric computation precision summary.

Provides strongly-typed summary return values for numeric computation output,
replacing dict[str, Any] return types in get_precision_summary() methods.
"""

from typing import TypedDict


class TypedDictNumericPrecisionSummary(TypedDict):
    """Summary of numeric computation precision.

    Attributes:
        precision_achieved: Precision level achieved in computation
        result_count: Number of numeric results
        has_errors: Whether computation errors occurred
        convergence_status: Whether computation converged
    """

    precision_achieved: int
    result_count: int
    has_errors: bool
    convergence_status: bool


__all__ = ["TypedDictNumericPrecisionSummary"]
