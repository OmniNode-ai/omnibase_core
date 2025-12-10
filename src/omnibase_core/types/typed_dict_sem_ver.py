from __future__ import annotations

"""
TypedDict for semantic version structure following SemVer specification.
"""

from typing import TypedDict


class TypedDictSemVer(TypedDict):
    """TypedDict for semantic version structure following SemVer specification."""

    major: int
    minor: int
    patch: int


__all__ = ["TypedDictSemVer"]
