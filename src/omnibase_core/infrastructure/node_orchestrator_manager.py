"""
NodeOrchestrator Manager Base Class

Base class for orchestrator nodes that need manager capabilities.
Handles boilerplate initialization for NodeOrchestrator + MixinNodeExecutor + MixinNodeIdFromContract.
"""

from typing import Any
from uuid import UUID

from omnibase_core.infrastructure.node_orchestrator import NodeOrchestrator
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_node_executor import MixinNodeExecutor
from omnibase_core.mixins.mixin_node_id_from_contract import MixinNodeIdFromContract
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeOrchestratorManager(  # type: ignore[misc]  # get_introspection_data signature differs between NodeOrchestrator and MixinEventDrivenNode - both implementations are valid
    NodeOrchestrator,
    MixinNodeExecutor,
    MixinNodeIdFromContract,
    MixinHealthCheck,
):
    """
    Base class for orchestrator nodes that need manager capabilities.

    Handles all the boilerplate initialization that every orchestrator node was duplicating.
    Use this instead of manually inheriting from multiple mixins.

    Features:
    - NodeOrchestrator core functionality
    - Manager lifecycle management via MixinNodeExecutor
    - Contract-based node ID loading via MixinNodeIdFromContract
    - Standardized health checks via MixinHealthCheck
    """

    @property  # type: ignore[override]  # MixinEventDrivenNode expects str, NodeCoreBase expects UUID
    def node_id(self) -> UUID:
        """Get the node ID from contract."""
        node_id_str = getattr(self, "_node_id", "00000000-0000-0000-0000-000000000000")
        return UUID(node_id_str) if isinstance(node_id_str, str) else node_id_str

    @node_id.setter
    def node_id(self, value: str | UUID) -> None:
        """Allow setting node_id (compatibility with NodeCoreBase)."""
        self._node_id = str(value) if isinstance(value, UUID) else value

    def __init__(self, container: ModelONEXContainer):
        """Initialize with proper mixin coordination."""
        # Initialize contract loading first
        MixinNodeIdFromContract.__init__(self)

        # Load node_id from contract
        self._node_id = self._load_node_id()

        # Get services from the infrastructure container via duck typing
        event_bus: Any = container.get_service("ProtocolEventBus")  # type: ignore[arg-type]
        metadata_loader: Any = container.get_service("ProtocolSchemaLoader")  # type: ignore[arg-type]

        # Initialize NodeOrchestrator
        NodeOrchestrator.__init__(self, container)

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
