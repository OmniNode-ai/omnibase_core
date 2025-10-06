from __future__ import annotations

import uuid
from typing import Dict, TypedDict

"""
Core analytics data structure.
Implements omnibase_spi protocols:
- ProtocolMetadataProvider: Metadata management capabilities
- Serializable: Data serialization/deserialization
- Validatable: Validation and verification
"""


from typing import TypedDict
from uuid import UUID


class TypedDictCoreAnalytics(TypedDict):
    """Core analytics data structure."""

    collection_id: UUID
    collection_name: str | None
    total_nodes: int
    active_nodes: int
    deprecated_nodes: int
    disabled_nodes: int
    has_issues: bool


__all__ = ["ModelTypedDictCoreAnalytics"]
