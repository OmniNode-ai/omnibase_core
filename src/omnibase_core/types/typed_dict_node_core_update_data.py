"""
Typed structure for core node data updates.
"""

from __future__ import annotations

from typing import TypedDict

from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_node_type import EnumNodeType


class TypedDictNodeCoreUpdateData(TypedDict, total=False):
    node_display_name: str
    description: str
    node_type: EnumNodeType
    status: EnumMetadataNodeStatus
    complexity: EnumConceptualComplexity


__all__ = ["TypedDictNodeCoreUpdateData"]
