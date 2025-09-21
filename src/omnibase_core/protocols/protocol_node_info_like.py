"""
NodeInfoLike Protocol.

Protocol for objects that can be converted to ModelNodeMetadataInfo.
"""

from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from ..enums.enum_metadata_node_status import EnumMetadataNodeStatus
    from ..models.metadata.model_semver import ModelSemVer


class NodeInfoLike(Protocol):
    """Protocol for objects that can be converted to ModelNodeMetadataInfo."""

    def __getattr__(self, name: str) -> Any:
        """Allow attribute access for node info properties."""
        ...


# Export for use
__all__ = ["NodeInfoLike"]
