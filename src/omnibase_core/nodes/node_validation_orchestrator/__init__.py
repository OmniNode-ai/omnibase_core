"""
Validation node implementations.

This module provides orchestrator nodes for validation workflows
in the ONEX framework.

Available Nodes:
    - :class:`NodeCrossRepoValidationOrchestrator`: Cross-repo validation
      with event emission for dashboard integration.

Import Example:
    .. code-block:: python

        from omnibase_core.nodes.node_validation_orchestrator import (
            NodeCrossRepoValidationOrchestrator,
            ModelCrossRepoValidationOrchestratorResult,
        )

See Also:
    - :mod:`omnibase_core.validation.cross_repo`: Validation engine
    - :mod:`omnibase_core.models.events.validation`: Event models

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from omnibase_core.models.validation.model_cross_repo_validation_orchestrator_result import (
    ModelCrossRepoValidationOrchestratorResult,
)
from omnibase_core.nodes.node_validation_orchestrator.node_cross_repo_validation_orchestrator import (
    NodeCrossRepoValidationOrchestrator,
)
from omnibase_core.nodes.node_validation_orchestrator.protocol_event_emitter import (
    ProtocolEventEmitter,
)

__all__ = [
    "NodeCrossRepoValidationOrchestrator",
    "ModelCrossRepoValidationOrchestratorResult",
    "ProtocolEventEmitter",
]
