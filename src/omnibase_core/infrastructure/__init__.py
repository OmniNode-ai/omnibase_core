"""Infrastructure module.

This module contains node bases and infrastructure services.

Re-exports:
    For convenience, this module re-exports cache backends from their canonical
    location in omnibase_core.backends.cache. While these work, prefer importing
    directly from omnibase_core.backends.cache for clarity:

    .. code-block:: python

        # Preferred - import from canonical location
        from omnibase_core.backends.cache import BackendCacheRedis, REDIS_AVAILABLE

        # Also works - re-exported here for convenience
        from omnibase_core.infrastructure import BackendCacheRedis, REDIS_AVAILABLE
"""

# Re-export from canonical location (backends.cache) for convenience
# NOTE: Prefer importing directly from omnibase_core.backends.cache
from omnibase_core.backends.cache import (
    REDIS_AVAILABLE,
    BackendCacheRedis,
)
from omnibase_core.infrastructure.execution.infra_phase_sequencer import (
    create_execution_plan,
)
from omnibase_core.infrastructure.node_base import NodeBase
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache
from omnibase_core.models.infrastructure.model_effect_transaction import (
    ModelEffectTransaction,
)

__all__ = [
    # Cache backends (OMN-1188) - from backends.cache
    "REDIS_AVAILABLE",
    "BackendCacheRedis",
    # Execution sequencing - from execution.infra_phase_sequencer
    "create_execution_plan",
    # Node bases
    "NodeBase",
    "NodeCoreBase",
    # Infrastructure classes
    "ModelCircuitBreaker",
    "ModelExecutionPlan",
    "ModelPhaseStep",
    "ModelComputeCache",
    "ModelEffectTransaction",
]
