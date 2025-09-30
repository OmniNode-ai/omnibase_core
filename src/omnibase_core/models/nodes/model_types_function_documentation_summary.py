"""
TypedDict for function documentation summary.

Replaces dict[str, Any] return type with structured typing.
"""

from __future__ import annotations

from typing import TypedDict


class ModelFunctionDocumentationSummaryType(TypedDict):
    """
    Typed dictionary for function documentation summary.

    Replaces dict[str, Any] return type from get_documentation_summary()
    with proper type structure.
    """

    has_documentation: bool
    has_examples: bool
    has_notes: bool
    examples_count: int
    notes_count: int
    quality_score: float


# Export for use
__all__ = ["ModelFunctionDocumentationSummaryType"]
