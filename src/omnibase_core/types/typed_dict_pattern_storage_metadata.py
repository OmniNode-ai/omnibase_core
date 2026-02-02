"""
TypedDict for pattern storage metadata.

Strongly-typed representation for metadata passed during pattern storage operations.
Follows ONEX one-model-per-file and TypedDict naming conventions.

This TypedDict represents the serialized metadata format for patterns stored
in the learned_patterns repository. It captures contextual information about
the pattern's origin and categorization.

Reference:
    - OMN-1780: Replace dict[str, Any] with typed models
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictPatternStorageMetadata(TypedDict, total=False):
    """Strongly-typed structure for pattern storage metadata.

    This TypedDict defines the schema for metadata passed to pattern storage
    operations. All fields are optional (total=False) to allow partial metadata.

    Attributes:
        tags: Optional tags for pattern categorization and discovery.
        learning_context: Context describing how/where the pattern was learned.
        additional_attributes: Extra key-value pairs for extensibility.
            Values must be strings to ensure JSON serialization compatibility.

    Example:
        >>> metadata: TypedDictPatternStorageMetadata = {
        ...     "tags": ["code_review", "python"],
        ...     "learning_context": "Extracted from successful PR reviews",
        ...     "additional_attributes": {"source": "pr_review", "team": "core"},
        ... }
    """

    tags: list[str]
    learning_context: str | None
    additional_attributes: dict[str, str]


__all__ = ["TypedDictPatternStorageMetadata"]
