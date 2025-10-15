"""
NodeOrchestratorService - Standard Production-Ready Orchestrator Node

Pre-composed with essential mixins for production use:
- Orchestrator semantics (workflow coordination, dependency management)
- Health monitoring (MixinHealthCheck)
- Event publishing (MixinEventBus)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for orchestrator nodes that coordinate multi-node workflows and manage dependencies.

Usage Example:
    ```python
    from omnibase_core.nodes.services.node_orchestrator_service import NodeOrchestratorService
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_orchestrator import ModelContractOrchestrator

    class NodeWorkflowOrchestrator(NodeOrchestratorService):
        '''Workflow orchestrator with automatic event coordination and metrics.'''

        async def execute_orchestration(self, contract: ModelContractOrchestrator) -> dict:
            # Emit workflow started event
            await self.publish_event(
                event_type="workflow_started",
                payload={"workflow_id": str(contract.workflow_id)},
                correlation_id=contract.correlation_id
            )

            # Coordinate subnode execution
            results = await self._execute_workflow(contract)

            # Emit workflow completed event
            await self.publish_event(
                event_type="workflow_completed",
                payload={
                    "workflow_id": str(contract.workflow_id),
                    "steps_completed": len(results)
                },
                correlation_id=contract.correlation_id
            )

            return results
    ```

Included Capabilities:
    - Workflow coordination with dependency tracking
    - Subnode health aggregation
    - Event emission for workflow lifecycle via MixinEventBus
    - Performance metrics for workflow execution via MixinMetrics
    - Correlation ID tracking across workflow steps
    - Health check aggregation from managed subnodes

Node Type: Orchestrator (Workflow coordination, multi-node management)
"""

from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator


class NodeOrchestratorService(
    NodeOrchestrator,
    MixinHealthCheck,
    MixinEventBus,
    MixinMetrics,
):
    """
    Standard Orchestrator Node Service.

    Combines NodeOrchestrator base class with essential production mixins:
    - Orchestrator semantics (workflow coordination, dependency management)
    - Health monitoring (MixinHealthCheck) - includes subnode health aggregation
    - Event publishing (MixinEventBus) - critical for workflow coordination
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        NodeOrchestratorService → NodeOrchestrator → MixinHealthCheck
        → MixinEventBus → MixinMetrics → NodeCoreBase → ABC

    This composition is optimized for:
    - Multi-step workflow coordination requiring event-driven communication
    - Dependency management across multiple subnodes
    - Workflow lifecycle tracking (started, in-progress, completed, failed)
    - Parallel execution coordination with result aggregation

    Why MixinEventBus is critical:
        Orchestrators emit many events during workflow execution:
        - Workflow lifecycle events (started, completed, failed)
        - Subnode coordination events
        - Progress updates
        - Error notifications

    For custom mixin compositions, inherit directly from NodeOrchestrator
    and add your desired mixins instead.
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize NodeOrchestratorService with container dependency injection.

        All mixin initialization is handled automatically via Python's MRO.
        Each mixin's __init__ is called in sequence, setting up:
        - Health check framework (with subnode aggregation support)
        - Event bus connection for workflow coordination
        - Metrics collectors for workflow performance tracking

        Args:
            container: ONEX container providing service dependencies
        """
        super().__init__(container)
