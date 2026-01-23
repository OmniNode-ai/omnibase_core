"""
Compute Profile Factories.

Provides default profiles for compute contracts with safe defaults.

Profile Types:
    - compute_pure: Pure computation, no I/O
"""

from collections.abc import Callable

from omnibase_core.enums import EnumNodeArchetype, EnumNodeType
from omnibase_core.models.contracts import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelContractCompute,
    ModelExecutionOrderingPolicy,
    ModelExecutionProfile,
    ModelHandlerBehavior,
    ModelInputValidationConfig,
    ModelOutputTransformationConfig,
    ModelParallelConfig,
    ModelPerformanceRequirements,
)

from ._utils import _create_minimal_event_type_subcontract, _parse_version


def get_compute_pure_profile(version: str = "1.0.0") -> ModelContractCompute:
    """
    Create a compute_pure profile.

    Pure computation profile with safe defaults:
    - Deterministic execution enabled
    - No parallel processing (single-threaded)
    - Memory optimization enabled
    - No intermediate result caching

    Args:
        version: The version to apply to the contract.

    Returns:
        A fully valid compute contract with pure computation settings.
    """
    semver = _parse_version(version)

    return ModelContractCompute(
        # Core identification
        name="compute_pure_profile",
        contract_version=semver,
        description="Pure computation profile with deterministic execution",
        node_type=EnumNodeType.COMPUTE_GENERIC,
        # Model specifications
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        # Performance requirements
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=5000,
            batch_operation_max_s=30,
            memory_limit_mb=512,
        ),
        # Algorithm configuration (required)
        algorithm=ModelAlgorithmConfig(
            algorithm_type="pure_computation",
            factors={
                "primary_factor": ModelAlgorithmFactorConfig(
                    weight=1.0,  # Single factor with weight 1.0
                    calculation_method="identity",
                    normalization_enabled=False,
                    caching_enabled=False,
                ),
            },
            normalization_method="none",
            precision_digits=6,
        ),
        # Parallel processing - disabled for pure computation
        parallel_processing=ModelParallelConfig(
            enabled=False,
            max_workers=1,
        ),
        # Input validation
        input_validation=ModelInputValidationConfig(
            strict_validation=True,
        ),
        # Output transformation
        output_transformation=ModelOutputTransformationConfig(),
        # Compute-specific settings
        deterministic_execution=True,  # Pure computation must be deterministic
        memory_optimization_enabled=True,
        intermediate_result_caching=False,  # No caching for pure computation
        # Subcontracts
        event_type=_create_minimal_event_type_subcontract(
            version=semver,
            primary_events=["compute_started", "compute_completed"],
            event_categories=["compute", "processing"],
        ),
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior configuration for pure computation
        behavior=ModelHandlerBehavior(
            node_archetype=EnumNodeArchetype.COMPUTE,
            purity="pure",  # Pure compute - no side effects
            idempotent=True,  # Pure functions are always idempotent
            concurrency_policy="parallel_ok",  # Pure functions safe to parallelize
            isolation_policy="none",  # No isolation needed for pure compute
            observability_level="minimal",  # Minimal overhead for pure compute
        ),
    )


# Profile registry mapping profile names to factory functions
# Thread Safety: This registry is immutable after module load.
# Factory functions create new instances on each call.
COMPUTE_PROFILES: dict[str, Callable[[str], ModelContractCompute]] = {
    "compute_pure": get_compute_pure_profile,
}
