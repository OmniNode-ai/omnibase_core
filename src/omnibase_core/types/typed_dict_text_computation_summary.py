"""TypedDict for text computation output summary.

Provides strongly-typed summary return values for text computation output,
replacing dict[str, Any] return types in get_text_summary() methods.
"""

from typing import TypedDict


class TypedDictTextComputationSummary(TypedDict):
    """Summary of text computation output.

    Attributes:
        language_detected: Language detected in text processing
        result_count: Number of text results
        average_confidence: Average confidence score
        has_warnings: Whether warnings were generated
        warning_count: Number of warnings
    """

    language_detected: str
    result_count: int
    average_confidence: float
    has_warnings: bool
    warning_count: int


__all__ = ["TypedDictTextComputationSummary"]
