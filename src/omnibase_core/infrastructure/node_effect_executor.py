"""
NodeEffect Executor Base Class

Proper base class that handles the boilerplate initialization for NodeEffect + MixinNodeExecutor.
This eliminates the need for every single node to manually wire up mixin initialization.
"""

from typing import Any
from uuid import UUID

from omnibase_core.infrastructure.node_effect import NodeEffect
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_node_executor import MixinNodeExecutor
from omnibase_core.mixins.mixin_node_id_from_contract import MixinNodeIdFromContract
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeEffectExecutor(  # type: ignore[misc]  # Signature incompatibility between NodeEffect and MixinEventDrivenNode get_introspection_data
    NodeEffect,
    MixinNodeExecutor,
    MixinNodeIdFromContract,
    MixinHealthCheck,
):
    """
    Proper base class for effect nodes that need executor capabilities.

    Handles all the boilerplate initialization that every node was duplicating.
    Use this instead of manually inheriting from multiple mixins.

    Features:
    - NodeEffect core functionality
    - Executor lifecycle management via MixinNodeExecutor
    - Contract-based node ID loading via MixinNodeIdFromContract
    - Standardized health checks via MixinHealthCheck
    """

    @property  # type: ignore[override]  # MixinEventDrivenNode expects str, NodeCoreBase expects UUID
    def node_id(self) -> UUID:
        """Get the node ID from contract."""
        return self._node_id

    @node_id.setter
    def node_id(self, value: str | UUID) -> None:
        """Allow setting node_id (compatibility with NodeCoreBase)."""
        self._node_id = UUID(value) if isinstance(value, str) else value

    def __init__(self, container: ModelONEXContainer):
        """Initialize with proper mixin coordination."""
        # Initialize contract loading first
        MixinNodeIdFromContract.__init__(self)

        # Load node_id from contract and convert to UUID
        node_id_str = self._load_node_id()
        self._node_id = UUID(node_id_str)

        # Get the real event bus from the container via duck typing
        event_bus: Any = container.get_service("ProtocolEventBus")  # type: ignore[arg-type]

        # Get metadata loader from the container
        metadata_loader: Any = container.get_service("ProtocolSchemaLoader")  # type: ignore[arg-type]

        # Initialize NodeEffect
        NodeEffect.__init__(self, container)

        # Initialize MixinNodeExecutor with proper arguments
        MixinNodeExecutor.__init__(
            self,
            node_id=self._node_id,
            event_bus=event_bus,
            metadata_loader=metadata_loader,
            registry=container,
        )

        # Initialize MixinHealthCheck
        MixinHealthCheck.__init__(self)
