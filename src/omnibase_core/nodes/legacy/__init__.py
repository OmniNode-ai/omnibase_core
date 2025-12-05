"""
Legacy Node Implementations - DEPRECATED

This module contains deprecated node implementations that are being phased out.
These classes are maintained for backwards compatibility but should not be used
for new development.

.. deprecated:: 0.4.0
    Use the new declarative node implementations instead:
    - NodeCompute → Use compute contracts with NodeCoreBase
    - NodeEffect → Use effect contracts with NodeCoreBase
    - NodeReducer → Use NodeReducer (formerly NodeReducerDeclarative)
    - NodeOrchestrator → Use NodeOrchestrator (formerly NodeOrchestratorDeclarative)

Migration Guide:
    See docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md for migration instructions.
"""

import warnings

# Emit deprecation warning when this module is imported
warnings.warn(
    "The omnibase_core.nodes.legacy module is deprecated and will be removed in v1.0.0. "
    "Migrate to the new declarative node implementations.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy exports - all deprecated node implementations
from omnibase_core.nodes.legacy.node_compute_legacy import NodeComputeLegacy
from omnibase_core.nodes.legacy.node_effect_legacy import NodeEffectLegacy
from omnibase_core.nodes.legacy.node_orchestrator_legacy import NodeOrchestratorLegacy
from omnibase_core.nodes.legacy.node_reducer_legacy import NodeReducerLegacy

__all__: list[str] = [
    "NodeComputeLegacy",
    "NodeEffectLegacy",
    "NodeOrchestratorLegacy",
    "NodeReducerLegacy",
]
