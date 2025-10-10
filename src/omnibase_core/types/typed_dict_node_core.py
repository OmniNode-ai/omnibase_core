"""
TypedDict for node core data.

Strongly-typed representation for node core data structure.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict
from uuid import UUID

from omnibase_core.models.core.model_semver import ModelSemVer


class TypedDictNodeCore(TypedDict):
    """Strongly-typed node core data structure."""

    node_id: UUID
    node_display_name: str | None
    description: str | None
    node_type: str
    status: str
    complexity: str
    version: ModelSemVer
    is_active: bool
    is_complex: bool


__all__ = ["TypedDictNodeCore"]
