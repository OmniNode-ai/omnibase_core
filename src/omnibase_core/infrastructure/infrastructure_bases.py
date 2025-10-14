"""
Infrastructure Base Classes

Consolidated imports for all infrastructure node base classes.
Eliminates boilerplate initialization across the infrastructure tool group.

Usage Examples:
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

# Infrastructure base classes - eliminate boilerplate
from omnibase_core.infrastructure.node_effect_executor import NodeEffectExecutor
from omnibase_core.infrastructure.node_orchestrator_manager import (
    NodeOrchestratorManager,
)
from omnibase_core.infrastructure.node_reducer_processor import NodeReducerProcessor

# Infrastructure container - available via canary implementation
from omnibase_core.nodes.canary.container import create_infrastructure_container

__all__ = [
    "NodeComputeEngine",
    "NodeEffectExecutor",
    "NodeOrchestratorManager",
    "NodeReducerProcessor",
    "create_infrastructure_container",
]
