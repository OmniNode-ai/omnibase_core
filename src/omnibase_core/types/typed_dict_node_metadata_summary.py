"""
TypedDict for node metadata summary.

Replaces dict[str, Any] return type with structured typing following ONEX patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictNodeMetadataSummary(TypedDict):
    """
    Typed dictionary for node metadata info summary.

    Replaces dict[str, Any] return type from get_summary()
    with proper type structure.
    """

    node_id: UUID
    node_name: str
    node_type: str
    status: str
    health: str
    version: ModelSemVer | None
    usage_count: int
    error_rate: float
    success_rate: float
    capabilities: list[str]
    tags: list[str]
    is_active: bool
    is_healthy: bool
    has_errors: bool
    capabilities_count: int
    tags_count: int
    is_high_usage: bool


__all__ = ["TypedDictNodeMetadataSummary"]
