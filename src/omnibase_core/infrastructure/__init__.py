"""Infrastructure module.

This module contains node bases and infrastructure services.
"""

# Re-export from canonical location (backends.cache)
from omnibase_core.backends.cache import (
    REDIS_AVAILABLE,
    BackendCacheRedis,
)
from omnibase_core.infrastructure.execution.phase_sequencer import (
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
    # Execution sequencing - from execution.phase_sequencer
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
