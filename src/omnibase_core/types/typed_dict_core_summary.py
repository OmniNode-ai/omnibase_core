from __future__ import annotations

"""
TypedDict for node core summary information.

Type-safe dictionary structure for core node metadata summaries.
"""

from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.core.model_semver import ModelSemVer


class TypedDictCoreSummary(TypedDict):
    """Type-safe dictionary for node core summary."""

    node_id: UUID
    node_name: str
    node_type: str  # EnumMetadataNodeType.value
    node_version: ModelSemVer
    status: str  # EnumMetadataNodeStatus.value
    health: str  # EnumRegistryStatus.value
    is_active: bool
    is_healthy: bool
    has_description: bool
    has_author: bool
