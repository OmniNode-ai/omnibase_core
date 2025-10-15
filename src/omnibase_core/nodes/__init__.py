"""
Omnibase Core - ONEX Four-Node Architecture

Node implementations for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR patterns.

VERSION: 1.0.0
STABILITY GUARANTEE: Node interfaces are frozen for code generation.
Breaking changes require major version bump.
"""

from omnibase_core.nodes.model_compute_input import ModelComputeInput
from omnibase_core.nodes.model_compute_output import ModelComputeOutput
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect

# Note: NodeOrchestrator and NodeReducer will be added after Phase 2 Agent 3 completion
# from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
# from omnibase_core.nodes.node_reducer import NodeReducer

__all__ = [
    "ModelComputeInput",
    "ModelComputeOutput",
    "NodeCompute",
    "NodeEffect",
    # "NodeOrchestrator",  # TODO: Phase 2 Agent 3
    # "NodeReducer",  # TODO: Phase 2 Agent 3
]
