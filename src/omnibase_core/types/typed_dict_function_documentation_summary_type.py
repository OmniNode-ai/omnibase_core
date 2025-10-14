"""
TypedDict for function documentation summary.

Strongly-typed representation for function documentation summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictFunctionDocumentationSummaryType(TypedDict):
    """
    Strongly-typed dictionary for function documentation summary.

    Replaces dict[str, Any] return type from get_documentation_summary()
    with proper type structure.
    """

    has_documentation: bool
    has_examples: bool
    has_notes: bool
    examples_count: int
    notes_count: int
    quality_score: float


__all__ = ["TypedDictFunctionDocumentationSummaryType"]
