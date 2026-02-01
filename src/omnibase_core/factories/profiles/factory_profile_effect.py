"""
Effect Profile Factories.

Provides default profiles for effect contracts with safe defaults.

Profile Types:
    - effect_idempotent: Idempotent effect with retries
"""

from collections.abc import Callable

from omnibase_core.enums import EnumNodeArchetype, EnumNodeType
from omnibase_core.models.contracts import (
    ModelBackupConfig,
    ModelContractEffect,
    ModelDescriptorRetryPolicy,
    ModelEffectRetryConfig,
    ModelExecutionOrderingPolicy,
    ModelExecutionProfile,
    ModelHandlerBehavior,
    ModelIOOperationConfig,
    ModelPerformanceRequirements,
    ModelTransactionConfig,
)

from ._utils import _create_minimal_event_type_subcontract, _parse_version


def get_effect_idempotent_profile(version: str = "1.0.0") -> ModelContractEffect:
    """
    Create an effect_idempotent profile.

    Idempotent effect with safe defaults:
    - Idempotent operations enabled
    - Retry policies configured
    - Audit trail enabled
    - Consistency validation enabled

    Args:
        version: The version to apply to the contract.

    Returns:
        A fully valid effect contract with idempotent settings.
    """
    semver = _parse_version(version)

    return ModelContractEffect(
        # Core identification
        name="effect_idempotent_profile",
        contract_version=semver,
        description="Idempotent effect profile with retry support and audit trail",
        node_type=EnumNodeType.EFFECT_GENERIC,
        # Model specifications
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        # Performance requirements
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=10000,  # Longer for I/O
            batch_operation_max_s=60,
            memory_limit_mb=256,
        ),
        # I/O operations (required)
        io_operations=[
            ModelIOOperationConfig(
                operation_type="generic_io",
                atomic=True,
                backup_enabled=True,
                timeout_seconds=30,
            ),
        ],
        # Transaction management
        transaction_management=ModelTransactionConfig(
            enabled=True,
            isolation_level="serializable",
            timeout_seconds=30,
        ),
        # Retry policies
        retry_policies=ModelEffectRetryConfig(
            max_attempts=3,
            base_delay_ms=1000,
            max_delay_ms=5000,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
        ),
        # Backup configuration
        backup_config=ModelBackupConfig(
            enabled=True,
            retention_days=3,
        ),
        # Effect-specific settings
        idempotent_operations=True,
        side_effect_logging_enabled=True,
        audit_trail_enabled=True,
        consistency_validation_enabled=True,
        # Subcontracts
        event_type=_create_minimal_event_type_subcontract(
            version=semver,
            primary_events=["effect_executed", "effect_completed"],
            event_categories=["effect", "io"],
        ),
        # Execution profile
        execution=ModelExecutionProfile(
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                deterministic_seed=True,
            ),
        ),
        # Handler behavior configuration for contract-driven execution
        behavior=ModelHandlerBehavior(
            node_archetype=EnumNodeArchetype.EFFECT,
            purity="side_effecting",  # Effects interact with external systems
            idempotent=True,  # This is the idempotent profile
            timeout_ms=30000,  # 30 second timeout for external operations
            concurrency_policy="parallel_ok",  # Idempotent effects can run in parallel
            isolation_policy="none",
            observability_level="standard",
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=3,
                backoff_strategy="exponential",
                base_delay_ms=1000,
            ),
            capability_outputs=["external_system"],  # Effects produce external outputs
        ),
    )


# Profile registry mapping profile names to factory functions
# Thread Safety: This registry is immutable after module load.
# Factory functions create new instances on each call.
EFFECT_PROFILES: dict[str, Callable[[str], ModelContractEffect]] = {
    "effect_idempotent": get_effect_idempotent_profile,
}
