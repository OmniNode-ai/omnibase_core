"""
Orchestrator Profile Factories.

Provides default profiles for orchestrator contracts with safe defaults.

Profile Types:
    - orchestrator_safe: Serial execution, no rollback, conservative
    - orchestrator_parallel: Parallel execution allowed
    - orchestrator_resilient: Retries, checkpointing enabled
"""

from collections.abc import Callable

from omnibase_core.enums import EnumNodeArchetype, EnumNodeType
from omnibase_core.models.contracts import (
    ModelActionEmissionConfig,
    ModelBranchingConfig,
    ModelContractOrchestrator,
    ModelDescriptorCircuitBreaker,
    ModelDescriptorRetryPolicy,
    ModelEventCoordinationConfig,
    ModelEventRegistryConfig,
    ModelExecutionOrderingPolicy,
    ModelExecutionProfile,
    ModelHandlerBehavior,
    ModelPerformanceRequirements,
    ModelWorkflowConfig,
)

from ._utils import _parse_version


def get_orchestrator_safe_profile(version: str = "1.0.0") -> ModelContractOrchestrator:
    """
    Create an orchestrator_safe profile.

    Safe profile with conservative settings:
    - Serial execution (no parallel branches)
    - No rollback
    - Conservative circuit breakers
    - Basic event coordination

    Args:
        version: The version to apply to the contract.

    Returns:
        A fully valid orchestrator contract with safe defaults.
    """
    return ModelContractOrchestrator(
        # Core identification
        name="orchestrator_safe_profile",
        contract_version=_parse_version(version),
        description="Safe orchestrator profile with serial execution and conservative settings",
        node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
        # Model specifications
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        # Performance requirements
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=5000,
            batch_operation_max_s=30,
            memory_limit_mb=512,
        ),
        # Orchestration configuration - SAFE
        action_emission=ModelActionEmissionConfig(
            emission_strategy="sequential",  # Safe: one at a time
            batch_size=1,
        ),
        workflow_coordination=ModelWorkflowConfig(
            execution_mode="serial",  # Safe: serial execution
            max_parallel_branches=1,  # Safe: no parallel branches
            checkpoint_enabled=False,  # Safe: no complex checkpointing
            checkpoint_interval_ms=100,  # Minimum allowed value
        ),
        conditional_branching=ModelBranchingConfig(
            max_branch_depth=3,  # Safe: limit branch depth
        ),
        # Event configuration
        event_registry=ModelEventRegistryConfig(
            discovery_enabled=False,  # Safe: manual registration
        ),
        event_coordination=ModelEventCoordinationConfig(
            coordination_strategy="sequential",
            buffer_size=10,
            correlation_enabled=False,  # Safe: no correlation
            correlation_timeout_ms=1000,  # Minimum reasonable value
        ),
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior configuration - conservative, serial execution
        behavior=ModelHandlerBehavior(
            node_archetype=EnumNodeArchetype.ORCHESTRATOR,
            purity="side_effecting",
            idempotent=False,
            concurrency_policy="serialized",
            isolation_policy="none",
            observability_level="standard",
        ),
    )


def get_orchestrator_parallel_profile(
    version: str = "1.0.0",
) -> ModelContractOrchestrator:
    """
    Create an orchestrator_parallel profile.

    Parallel profile with parallel execution enabled:
    - Parallel execution allowed
    - Multiple parallel branches
    - Event correlation enabled

    Args:
        version: The version to apply to the contract.

    Returns:
        A fully valid orchestrator contract with parallel execution enabled.
    """
    return ModelContractOrchestrator(
        # Core identification
        name="orchestrator_parallel_profile",
        contract_version=_parse_version(version),
        description="Parallel orchestrator profile with concurrent execution support",
        node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
        # Model specifications
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        # Performance requirements
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=5000,
            batch_operation_max_s=60,  # Longer for parallel ops
            memory_limit_mb=1024,  # More memory for parallel
        ),
        # Orchestration configuration - PARALLEL
        action_emission=ModelActionEmissionConfig(
            emission_strategy="batch",
            batch_size=5,
        ),
        workflow_coordination=ModelWorkflowConfig(
            execution_mode="parallel",  # Parallel execution
            max_parallel_branches=4,  # Allow parallel branches
            checkpoint_enabled=False,
            checkpoint_interval_ms=100,  # Minimum allowed value
        ),
        conditional_branching=ModelBranchingConfig(
            max_branch_depth=5,
        ),
        # Event configuration
        event_registry=ModelEventRegistryConfig(
            discovery_enabled=True,
        ),
        event_coordination=ModelEventCoordinationConfig(
            coordination_strategy="buffered",
            buffer_size=100,
            correlation_enabled=True,
            correlation_timeout_ms=5000,
        ),
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior configuration - parallel execution allowed
        behavior=ModelHandlerBehavior(
            node_archetype=EnumNodeArchetype.ORCHESTRATOR,
            purity="side_effecting",
            idempotent=False,
            concurrency_policy="parallel_ok",
            isolation_policy="none",
            observability_level="standard",
        ),
    )


def get_orchestrator_resilient_profile(
    version: str = "1.0.0",
) -> ModelContractOrchestrator:
    """
    Create an orchestrator_resilient profile.

    Resilient profile with checkpointing and retries:
    - Checkpointing enabled
    - Longer timeouts
    - Failure isolation

    Args:
        version: The version to apply to the contract.

    Returns:
        A fully valid orchestrator contract with resilience features enabled.
    """
    return ModelContractOrchestrator(
        # Core identification
        name="orchestrator_resilient_profile",
        contract_version=_parse_version(version),
        description="Resilient orchestrator profile with checkpointing and fault tolerance",
        node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
        # Model specifications
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        # Performance requirements
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=10000,  # Longer for retries
            batch_operation_max_s=120,
            memory_limit_mb=2048,
        ),
        # Orchestration configuration - RESILIENT
        action_emission=ModelActionEmissionConfig(
            emission_strategy="sequential",
            batch_size=1,
        ),
        workflow_coordination=ModelWorkflowConfig(
            execution_mode="serial",
            max_parallel_branches=1,
            checkpoint_enabled=True,  # Resilient: checkpointing
            checkpoint_interval_ms=1000,  # Checkpoint every second
        ),
        conditional_branching=ModelBranchingConfig(
            max_branch_depth=5,
        ),
        # Event configuration
        event_registry=ModelEventRegistryConfig(
            discovery_enabled=True,
        ),
        event_coordination=ModelEventCoordinationConfig(
            coordination_strategy="buffered",
            buffer_size=50,
            correlation_enabled=True,
            correlation_timeout_ms=10000,  # Longer timeout
        ),
        # Resilience settings
        failure_isolation_enabled=True,
        monitoring_enabled=True,
        metrics_collection_enabled=True,
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior configuration - resilient with retries and circuit breaker
        behavior=ModelHandlerBehavior(
            node_archetype=EnumNodeArchetype.ORCHESTRATOR,
            purity="side_effecting",
            idempotent=True,  # Resilient implies idempotent for safe retries
            concurrency_policy="serialized",
            isolation_policy="none",
            observability_level="verbose",  # More observability for resilient workflows
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=3,
                backoff_strategy="exponential",
            ),
            circuit_breaker=ModelDescriptorCircuitBreaker(
                enabled=True,
                failure_threshold=5,
            ),
        ),
    )


# Profile registry mapping profile names to factory functions
# Thread Safety: This registry is immutable after module load.
# Factory functions create new instances on each call.
ORCHESTRATOR_PROFILES: dict[str, Callable[[str], ModelContractOrchestrator]] = {
    "orchestrator_safe": get_orchestrator_safe_profile,
    "orchestrator_parallel": get_orchestrator_parallel_profile,
    "orchestrator_resilient": get_orchestrator_resilient_profile,
}
