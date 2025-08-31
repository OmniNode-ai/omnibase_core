"""
Infrastructure Service Base Classes

Consolidated imports for all infrastructure node service base classes.
Eliminates boilerplate initialization across the infrastructure tool group.

Usage Examples:
    from omnibase_core.core.infrastructure_service_bases import (
        NodeEffectService,
        NodeComputeService,
        NodeReducerService,
        NodeOrchestratorService
    )

    class MyEffectNode(NodeEffectService):
        def __init__(self, container):
            super().__init__(container)  # All setup handled!
"""

from omnibase_core.core.node_compute_service import NodeComputeService

# Infrastructure service base classes - eliminate boilerplate
from omnibase_core.core.node_effect_service import NodeEffectService
from omnibase_core.core.node_orchestrator_service import NodeOrchestratorService
from omnibase_core.core.node_reducer_service import NodeReducerService

# Infrastructure container - TODO: Implement when tools/infrastructure module is available
# from omnibase_core.tools.infrastructure.container import create_infrastructure_container

__all__ = [
    "NodeComputeService",
    "NodeEffectService",
    "NodeOrchestratorService",
    "NodeReducerService",
    # "create_infrastructure_container",  # TODO: Uncomment when infrastructure module is available
]
