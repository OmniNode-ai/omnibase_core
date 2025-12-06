"""
Legacy node implementations for backwards compatibility.

.. deprecated:: 0.4.0
    Legacy nodes are deprecated. Use the declarative node implementations instead:
    - NodeOrchestratorLegacy -> NodeOrchestrator
    - NodeReducerLegacy -> NodeReducer
    - NodeComputeLegacy -> NodeCompute
    - NodeEffectLegacy -> NodeEffect

    See docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md for migration guide.
"""

from omnibase_core.nodes.legacy.node_orchestrator_legacy import NodeOrchestratorLegacy

__all__ = [
    "NodeOrchestratorLegacy",
]
