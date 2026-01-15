"""
Contract Profile Definitions.

This subpackage contains default profile definitions for each node type.
Each profile factory function returns a fully valid contract with
safe defaults appropriate for the profile type.

Profile Types:
    Orchestrator:
        - orchestrator_safe: Serial execution, no rollback, conservative
        - orchestrator_parallel: Parallel execution allowed
        - orchestrator_resilient: Retries, checkpointing enabled

    Reducer:
        - reducer_fsm_basic: Basic FSM reducer

    Effect:
        - effect_idempotent: Idempotent effect with retries

    Compute:
        - compute_pure: Pure computation, no I/O

Thread Safety:
    Profile registries (ORCHESTRATOR_PROFILES, REDUCER_PROFILES, etc.) are
    module-level dictionaries that are immutable after module initialization.
    Factory functions create new contract instances on each call, making them
    safe to use from multiple threads without synchronization.
"""

from omnibase_core.factories.profiles.factory_profile_compute import (
    COMPUTE_PROFILES,
    get_compute_pure_profile,
)
from omnibase_core.factories.profiles.factory_profile_effect import (
    EFFECT_PROFILES,
    get_effect_idempotent_profile,
)
from omnibase_core.factories.profiles.factory_profile_orchestrator import (
    ORCHESTRATOR_PROFILES,
    get_orchestrator_parallel_profile,
    get_orchestrator_resilient_profile,
    get_orchestrator_safe_profile,
)
from omnibase_core.factories.profiles.factory_profile_reducer import (
    REDUCER_PROFILES,
    get_reducer_fsm_basic_profile,
)

__all__ = [
    # Orchestrator profiles
    "ORCHESTRATOR_PROFILES",
    "get_orchestrator_safe_profile",
    "get_orchestrator_parallel_profile",
    "get_orchestrator_resilient_profile",
    # Reducer profiles
    "REDUCER_PROFILES",
    "get_reducer_fsm_basic_profile",
    # Effect profiles
    "EFFECT_PROFILES",
    "get_effect_idempotent_profile",
    # Compute profiles
    "COMPUTE_PROFILES",
    "get_compute_pure_profile",
]
