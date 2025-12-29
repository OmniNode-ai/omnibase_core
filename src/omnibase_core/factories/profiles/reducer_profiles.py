"""
Reducer Profile Factories.

Provides default profiles for reducer contracts with safe defaults.

Profile Types:
    - reducer_fsm_basic: Basic FSM reducer with simple state machine
"""

from collections.abc import Callable

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import (
    ModelContractReducer,
    ModelExecutionOrderingPolicy,
    ModelExecutionProfile,
    ModelHandlerDescriptor,
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
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


def _parse_version(version: str) -> ModelSemVer:
    """Parse version string to ModelSemVer."""
    parts = version.split(".")
    return ModelSemVer(
        major=int(parts[0]) if len(parts) > 0 else 1,
        minor=int(parts[1]) if len(parts) > 1 else 0,
        patch=int(parts[2]) if len(parts) > 2 else 0,
    )


def _create_minimal_fsm_subcontract(version: ModelSemVer) -> ModelFSMSubcontract:
    """
    Create a minimal valid FSM subcontract for reducer profiles.

    Provides a basic three-state FSM (idle -> processing -> completed)
    with required operations for critical state machine actions.
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


def _create_minimal_event_type_subcontract(
    version: ModelSemVer,
) -> ModelEventTypeSubcontract:
    """
    Create a minimal valid event type subcontract for reducer profiles.

    Provides basic event configuration for reducer participation
    in event-driven workflows.
    """
    return ModelEventTypeSubcontract(
        version=version,
        primary_events=["state_changed", "reduction_completed"],
        event_categories=["state", "reducer"],
        publish_events=True,
        subscribe_events=True,
        event_routing="default",
    )


def get_reducer_fsm_basic_profile(version: str = "1.0.0") -> ModelContractReducer:
    """
    Create a reducer_fsm_basic profile.

    Basic FSM reducer with simple state machine:
    - Three-state FSM (idle -> processing -> completed)
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
        version=semver,
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
        event_type=_create_minimal_event_type_subcontract(semver),
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior descriptor
        descriptor=ModelHandlerDescriptor(
            handler_kind="reducer",
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
