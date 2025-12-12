"""TypedDict for node introspection data."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from omnibase_core.types.typed_dict_node_capabilities import TypedDictNodeCapabilities


class TypedDictNodeIntrospection(TypedDict):
    """
    TypedDict for node introspection data.

    Provides comprehensive information about a node for monitoring
    and debugging purposes.

    Attributes:
        node_id: Unique identifier for the node
        node_type: Class name of the node
        version: Semantic version string
        created_at: ISO-formatted creation timestamp
        state: Current node state
        metrics: Performance metrics dictionary
        capabilities: Supported node capabilities
        contract_loaded: Whether contract data is loaded
        container_available: Whether container is available
    """

    node_id: UUID
    node_type: str
    version: (
        str  # Serialization boundary - string version appropriate for introspection
    )
    created_at: str
    state: dict[str, str]
    metrics: dict[str, float]
    capabilities: TypedDictNodeCapabilities
    contract_loaded: bool
    container_available: bool


__all__ = ["TypedDictNodeIntrospection"]
