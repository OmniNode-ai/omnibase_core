from __future__ import annotations

"""
TypedDict for dependency information.
"""


from datetime import datetime
from typing import TypedDict

from .typed_dict_sem_ver import TypedDictSemVer


class TypedDictDependencyInfo(TypedDict):
    """TypedDict for dependency information."""

    dependency_name: str
    dependency_version: TypedDictSemVer
    required_version: TypedDictSemVer
    status: str  # "satisfied", "missing", "outdated", "conflict"
    installed_at: NotRequired[datetime]
