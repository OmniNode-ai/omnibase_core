"""TypedDict for secondary intent entries.

Defines the TypedDictSecondaryIntent TypedDict for secondary intent entries
returned from intent classification operations.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictSecondaryIntent(TypedDict, total=False):
    """Typed structure for secondary intent entries.

    Provides stronger typing for intent classification results. With total=False,
    all fields are optional, allowing any subset to be provided.

    Attributes:
        intent_category: The category of the secondary intent.
        confidence: Confidence score for this intent (0.0 to 1.0).
        description: Human-readable description of the intent.
        keywords: Keywords associated with this intent.
        parent_intent: Parent intent category, if hierarchical.
    """

    intent_category: str
    confidence: float
    description: str
    keywords: list[str]
    parent_intent: str | None


__all__ = ["TypedDictSecondaryIntent"]
