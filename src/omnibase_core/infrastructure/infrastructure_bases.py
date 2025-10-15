"""
Infrastructure Base Classes

Consolidated imports for all infrastructure node base classes and service wrappers.
Eliminates boilerplate initialization across the infrastructure tool group.

RECOMMENDED: Use Service Wrappers (Standard Production-Ready Compositions)
    Service wrappers provide pre-configured mixin compositions for production use:
    - NodeEffectService: Effect + HealthCheck + EventBus + Metrics
    - NodeComputeService: Compute + HealthCheck + Caching + Metrics
    - NodeOrchestratorService: Orchestrator + HealthCheck + EventBus + Metrics
    - NodeReducerService: Reducer + HealthCheck + Caching + Metrics

Usage Examples (Recommended):
    from omnibase_core.infrastructure.infrastructure_bases import (
        NodeEffectService,
        NodeComputeService,
        NodeReducerService,
        NodeOrchestratorService
    )

    class MyDatabaseWriter(NodeEffectService):
        async def execute_effect(self, contract):
            # Health checks, events, and metrics included automatically!
            result = await self.database.write(contract.input_data)
            await self.publish_event("write_completed", {...})
            return result

Legacy Usage (Backward Compatibility):
    from omnibase_core.infrastructure.infrastructure_bases import (
        NodeEffectExecutor,
        NodeComputeEngine,
        NodeReducerProcessor,
        NodeOrchestratorManager
    )

    class MyEffectNode(NodeEffectExecutor):
        def __init__(self, container):
            super().__init__(container)  # All setup handled!
"""

from omnibase_core.infrastructure.node_compute_engine import NodeComputeEngine

# Infrastructure base classes - legacy support (eliminate boilerplate)
from omnibase_core.infrastructure.node_effect_executor import NodeEffectExecutor
from omnibase_core.infrastructure.node_orchestrator_manager import (
    NodeOrchestratorManager,
)
from omnibase_core.infrastructure.node_reducer_processor import NodeReducerProcessor

# Infrastructure container - available via canary implementation
from omnibase_core.nodes.canary.container import create_infrastructure_container

# Standard service wrappers - RECOMMENDED for production use
# Pre-composed with health checks, events/caching, and metrics
from omnibase_core.nodes.services.node_compute_service import NodeComputeService
from omnibase_core.nodes.services.node_effect_service import NodeEffectService
from omnibase_core.nodes.services.node_orchestrator_service import (
    NodeOrchestratorService,
)
from omnibase_core.nodes.services.node_reducer_service import NodeReducerService

__all__ = [
    # Legacy infrastructure classes (backward compatibility)
    "NodeComputeEngine",
    "NodeEffectExecutor",
    "NodeOrchestratorManager",
    "NodeReducerProcessor",
    "create_infrastructure_container",
    # Standard service wrappers (RECOMMENDED)
    "NodeEffectService",
    "NodeComputeService",
    "NodeOrchestratorService",
    "NodeReducerService",
]
