"""
NodeCompute Service Base Class

Base class for compute nodes that need service capabilities.
Handles boilerplate initialization for NodeCompute + MixinNodeService + MixinNodeIdFromContract.
"""

from omnibase.core.node_compute import NodeCompute
from omnibase.core.onex_container import ONEXContainer
from omnibase.mixin.mixin_health_check import MixinHealthCheck
from omnibase.mixin.mixin_node_id_from_contract import MixinNodeIdFromContract
from omnibase.mixin.mixin_node_service import MixinNodeService


class NodeComputeService(
    NodeCompute, MixinNodeService, MixinNodeIdFromContract, MixinHealthCheck
):
    """
    Base class for compute nodes that need service capabilities.

    Handles all the boilerplate initialization that every compute node was duplicating.
    Use this instead of manually inheriting from multiple mixins.

    Features:
    - NodeCompute core functionality
    - Service lifecycle management via MixinNodeService
    - Contract-based node ID loading via MixinNodeIdFromContract
    - Standardized health checks via MixinHealthCheck
    """

    @property
    def node_id(self) -> str:
        """Get the node ID from contract."""
        return getattr(self, "_node_id", "unknown")

    @node_id.setter
    def node_id(self, value: str) -> None:
        """Allow setting node_id (compatibility with NodeCoreBase)."""
        self._node_id = value

    def __init__(self, container: ONEXContainer):
        """Initialize with proper mixin coordination."""
        # Initialize contract loading first
        MixinNodeIdFromContract.__init__(self)

        # Load node_id from contract
        self._node_id = self._load_node_id()

        # Get services from the infrastructure container via duck typing
        event_bus = container.get_service("ProtocolEventBus")
        metadata_loader = container.get_service("ProtocolSchemaLoader")

        # Initialize NodeCompute
        NodeCompute.__init__(self, container)

        # Initialize MixinNodeService with proper arguments
        MixinNodeService.__init__(
            self,
            node_id=self._node_id,
            event_bus=event_bus,
            metadata_loader=metadata_loader,
            registry=container,
        )

        # Initialize MixinHealthCheck
        MixinHealthCheck.__init__(self)
