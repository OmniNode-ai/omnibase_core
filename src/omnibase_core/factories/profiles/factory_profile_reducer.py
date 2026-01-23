"""
Reducer Profile Factories.

Provides default profiles for reducer contracts with safe defaults.

Profile Types:
    - reducer_fsm_basic: Basic FSM reducer with simple state machine
"""

from collections.abc import Callable

from omnibase_core.enums import EnumNodeArchetype, EnumNodeType
from omnibase_core.models.contracts import (
    ModelContractReducer,
    ModelExecutionOrderingPolicy,
    ModelExecutionProfile,
    ModelHandlerBehavior,
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.fsm.model_fsm_operation import ModelFSMOperation
from omnibase_core.models.primitives.model_semver import ModelSemVer

from ._utils import _create_minimal_event_type_subcontract, _parse_version


def _create_minimal_fsm_subcontract(version: ModelSemVer) -> ModelFSMSubcontract:
    """
    Create a minimal valid FSM subcontract for reducer profiles.

    Provides a basic four-state FSM (idle -> processing -> completed, with error handling)
    with required operations for critical state machine actions.

    States:
        - idle: Initial state
        - processing: Active processing state
        - completed: Terminal success state
        - error: Recoverable error state
    """
    return ModelFSMSubcontract(
        version=version,
        state_machine_name="reducer_fsm",
        state_machine_version=version,
        description="Basic FSM for reducer profile",
        states=[
            ModelFSMStateDefinition(
                version=version,
                state_name="idle",
                state_type="operational",
                description="Initial idle state",
            ),
            ModelFSMStateDefinition(
                version=version,
                state_name="processing",
                state_type="operational",
                description="Processing state",
            ),
            ModelFSMStateDefinition(
                version=version,
                state_name="completed",
                state_type="terminal",
                description="Terminal completed state",
                is_terminal=True,
                is_recoverable=False,
            ),
            ModelFSMStateDefinition(
                version=version,
                state_name="error",
                state_type="error",
                description="Error state",
                is_terminal=False,
                is_recoverable=True,
            ),
        ],
        initial_state="idle",
        terminal_states=["completed"],
        transitions=[
            ModelFSMStateTransition(
                version=version,
                transition_name="start_processing",
                from_state="idle",
                to_state="processing",
                trigger="start",
            ),
            ModelFSMStateTransition(
                version=version,
                transition_name="complete_processing",
                from_state="processing",
                to_state="completed",
                trigger="complete",
            ),
            ModelFSMStateTransition(
                version=version,
                transition_name="handle_error",
                from_state="processing",
                to_state="error",
                trigger="error",
            ),
            ModelFSMStateTransition(
                version=version,
                transition_name="recover_from_error",
                from_state="error",
                to_state="idle",
                trigger="recover",
            ),
        ],
        operations=[
            ModelFSMOperation(
                operation_name="transition",
                operation_type="synchronous",
                description="State transition operation",
                requires_atomic_execution=True,
                supports_rollback=True,
            ),
            ModelFSMOperation(
                operation_name="snapshot",
                operation_type="synchronous",
                description="State snapshot operation",
                requires_atomic_execution=True,
                supports_rollback=True,
            ),
            ModelFSMOperation(
                operation_name="restore",
                operation_type="synchronous",
                description="State restore operation",
                requires_atomic_execution=True,
                supports_rollback=True,
            ),
        ],
    )


def get_reducer_fsm_basic_profile(version: str = "1.0.0") -> ModelContractReducer:
    """
    Create a reducer_fsm_basic profile.

    Basic FSM reducer with simple state machine:
    - Four-state FSM (idle -> processing -> completed, with error handling)
    - Basic event type configuration
    - Incremental processing enabled

    Args:
        version: The version to apply to the contract.

    Returns:
        A fully valid reducer contract with basic FSM.
    """
    semver = _parse_version(version)

    return ModelContractReducer(
        # Core identification
        name="reducer_fsm_basic_profile",
        contract_version=semver,
        description="Basic FSM reducer profile with simple state machine",
        node_type=EnumNodeType.REDUCER_GENERIC,
        # Model specifications
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        # Performance requirements
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=5000,
            batch_operation_max_s=30,
            memory_limit_mb=512,
        ),
        # Reducer-specific settings
        order_preserving=False,
        incremental_processing=True,
        result_caching_enabled=True,
        partial_results_enabled=True,
        # Subcontracts (use alias name for mypy compatibility)
        state_transitions=_create_minimal_fsm_subcontract(semver),
        event_type=_create_minimal_event_type_subcontract(
            version=semver,
            primary_events=["state_changed", "reduction_completed"],
            event_categories=["state", "reducer"],
            subscribe_events=True,
        ),
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior configuration
        behavior=ModelHandlerBehavior(
            node_archetype=EnumNodeArchetype.REDUCER,
            purity="side_effecting",  # Reducers modify state
            idempotent=True,  # FSM transitions should be idempotent
            concurrency_policy="singleflight",  # Only one state transition at a time
            isolation_policy="none",
            observability_level="standard",
        ),
    )


# Profile registry mapping profile names to factory functions
# Thread Safety: This registry is immutable after module load.
# Factory functions create new instances on each call.
REDUCER_PROFILES: dict[str, Callable[[str], ModelContractReducer]] = {
    "reducer_fsm_basic": get_reducer_fsm_basic_profile,
}
