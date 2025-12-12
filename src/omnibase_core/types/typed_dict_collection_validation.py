"""
TypedDict for collection validation results.

This module provides the typed dictionary structure for collection-level
validation results used by ModelMetadataToolCollection.
"""

from __future__ import annotations

from typing import TypedDict

from .typed_dict_tool_validation import TypedDictToolValidation


class TypedDictCollectionValidation(TypedDict):
    """Validation result for the entire tool collection."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    tool_validations: dict[str, TypedDictToolValidation]


__all__ = [
    "TypedDictCollectionValidation",
]
