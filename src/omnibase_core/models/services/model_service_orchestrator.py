"""
ModelServiceOrchestrator - Standard Production-Ready Orchestrator Node

Pre-composed with essential mixins for production use:
- Persistent service mode (MixinNodeService) - long-lived MCP servers, tool invocation
- Orchestrator semantics (workflow coordination, dependency management)
- Health monitoring (MixinHealthCheck)
- Event publishing (MixinEventBus)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for orchestrator nodes that coordinate multi-node workflows and manage dependencies.

Usage Example:
    ```python
    from omnibase_core.models.services.model_service_orchestrator import ModelServiceOrchestrator
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_orchestrator import ModelContractOrchestrator

    class NodeWorkflowOrchestrator(ModelServiceOrchestrator):
        '''Workflow orchestrator with automatic event coordination and metrics.'''

        async def execute_orchestration(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
            # Emit workflow started event
            await self.publish_event(
                event_type="workflow_started",
                payload={"workflow_id": str(input_data.workflow_id)},
                correlation_id=input_data.correlation_id
            )

            # Coordinate subnode execution
            results = await self._execute_workflow(input_data)

            # Emit workflow completed event
            await self.publish_event(
                event_type="workflow_completed",
                payload={
                    "workflow_id": str(input_data.workflow_id),
                    "steps_completed": len(results.completed_steps)
                },
                correlation_id=input_data.correlation_id
            )

            return results
    ```

Included Capabilities:
    - Persistent service mode with TOOL_INVOCATION handling (MixinNodeService)
    - Service lifecycle management (start_service_mode, stop_service_mode)
    - Workflow coordination with dependency tracking
    - Subnode health aggregation
    - Event emission for workflow lifecycle via MixinEventBus
    - Performance metrics for workflow execution via MixinMetrics
    - Correlation ID tracking across workflow steps
    - Health check aggregation from managed subnodes

Node Type: Orchestrator (Workflow coordination, multi-node management)
"""

from typing import Any

from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.mixins.mixin_node_service import MixinNodeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator


class ModelServiceOrchestrator(  # type: ignore[misc]
    MixinNodeService,
    NodeOrchestrator,
    MixinHealthCheck,
    MixinEventBus[Any, Any],
    MixinMetrics,
):
    """
    Standard Orchestrator Node Service.

    Combines NodeOrchestrator base class with essential production mixins:
    - Persistent service mode (MixinNodeService) - run as long-lived tool service
    - Orchestrator semantics (workflow coordination, dependency management)
    - Health monitoring (MixinHealthCheck) - includes subnode health aggregation
    - Event publishing (MixinEventBus) - critical for workflow coordination
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        ModelServiceOrchestrator → MixinNodeService → NodeOrchestrator → MixinHealthCheck
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
        Initialize ModelServiceOrchestrator with container dependency injection.

        All mixin initialization is handled automatically via Python's MRO.
        Each mixin's __init__ is called in sequence, setting up:
        - Health check framework (with subnode aggregation support)
        - Event bus connection for workflow coordination
        - Metrics collectors for workflow performance tracking

        Args:
            container: ONEX container providing service dependencies
        """
        super().__init__(container)
