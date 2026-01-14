"""
TypedDict for semantic version structure following SemVer specification.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictSemVer(TypedDict):
    major: int
    minor: int
    patch: int


__all__ = ["TypedDictSemVer"]
