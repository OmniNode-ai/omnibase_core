"""
TypedDict for dependency information.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict

from .typed_dict_sem_ver import TypedDictSemVer


class TypedDictDependencyInfo(TypedDict):
    dependency_name: str
    dependency_version: TypedDictSemVer
    required_version: TypedDictSemVer
    status: str  # "satisfied", "missing", "outdated", "conflict"
    installed_at: NotRequired[datetime]


__all__ = ["TypedDictDependencyInfo"]
