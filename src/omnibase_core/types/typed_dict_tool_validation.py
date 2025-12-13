"""
TypedDict for tool validation results.

This module provides the typed dictionary structure for individual tool
validation results used by ModelMetadataToolCollection.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictToolValidation(TypedDict):
    """Validation result for a single tool in the collection."""

    valid: bool
    errors: list[str]
    warnings: list[str]


__all__ = [
    "TypedDictToolValidation",
]
