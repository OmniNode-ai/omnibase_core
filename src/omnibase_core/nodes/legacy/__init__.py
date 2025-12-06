"""
Legacy node implementations for backwards compatibility.

.. deprecated:: 0.4.0
    Legacy nodes are deprecated. Use the declarative node implementations instead:
    - NodeOrchestratorLegacy -> NodeOrchestrator
    - NodeReducerLegacy -> NodeReducer

    See docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md for migration guide.
"""

import warnings

# Emit deprecation warning on module import
warnings.warn(
    "The omnibase_core.nodes.legacy module is deprecated since v0.4.0. "
    "Use omnibase_core.nodes instead (NodeOrchestrator, NodeReducer, NodeCompute, NodeEffect). "
    "See docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)

from omnibase_core.nodes.legacy.node_orchestrator_legacy import NodeOrchestratorLegacy

__all__ = [
    "NodeOrchestratorLegacy",
]
