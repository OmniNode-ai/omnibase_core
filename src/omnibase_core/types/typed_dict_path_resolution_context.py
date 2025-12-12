"""TypedDictPathResolutionContext.

TypedDict for path resolution error context in compute path resolver.

This provides type-safe context information for path resolution errors
without resorting to dict[str, Any].
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictPathResolutionContext(TypedDict, total=False):
    """
    Context information for path resolution errors.

    All fields are optional (total=False) to allow partial context.

    Attributes:
        path: The original path expression that failed to resolve
        segment: The specific segment where resolution failed
        available_keys: List of available keys/attributes at failure point
    """

    path: str
    segment: str
    available_keys: list[str]


__all__ = ["TypedDictPathResolutionContext"]
