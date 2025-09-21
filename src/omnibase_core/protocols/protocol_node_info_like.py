"""
NodeInfoLike Protocol.

Protocol for objects that can be converted to ModelNodeMetadataInfo.
"""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from ..enums.enum_metadata_node_status import EnumMetadataNodeStatus
    from ..models.metadata.model_semver import ModelSemVer


@runtime_checkable
class NodeInfoLike(Protocol):
    """
    Protocol for objects that can be converted to ModelNodeMetadataInfo.

    Defines the minimum interface required for node-like objects
    that can be processed by the metadata system.
    """

    # Core required attributes using UUID-based entity references
    node_id: UUID
    name: str
    description: str

    def __getattr__(self, name: str) -> Any:
        """Allow attribute access for additional node info properties."""
        ...


# Export for use
__all__ = ["NodeInfoLike"]
