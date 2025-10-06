"""Documentation Summary Filtered Model.

Type-safe dictionary for filtered documentation summary (quality_score excluded).
"""

from typing import TypedDict


class ModelDocumentationSummaryFiltered(TypedDict):
    """Type-safe dictionary for filtered documentation summary (quality_score excluded)."""

    has_documentation: bool
    has_examples: bool
    has_notes: bool
    examples_count: int
    notes_count: int
