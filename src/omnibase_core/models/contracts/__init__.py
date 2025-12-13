"""Contract Models for ONEX Four-Node Architecture.

This module provides Pydantic models for validating and managing contract
definitions across the ONEX four-node architecture (EFFECT, COMPUTE, REDUCER,
ORCHESTRATOR). Contracts define the interface and behavior expectations for
nodes in the system.

Key Model Categories:
    Foundation Models:
        Models that define core contract structures and metadata.
        - ModelContractBase: Base class for all contract types
        - ModelContractFingerprint: Cryptographic fingerprint for contract integrity
        - ModelContractMeta: Meta-model defining schema for all node contracts
        - ModelContractNodeMetadata: Contract-specific node metadata
        - ModelContractVersion: Semantic versioning for contracts
        - ModelDriftDetails: Structured details about contract drift
        - ModelDriftResult: Result of drift detection between contract versions

    Primary Contract Models:
        Contract definitions for each node type in the ONEX architecture.
        - ModelContractCompute: Contract for COMPUTE nodes (data processing)
        - ModelContractEffect: Contract for EFFECT nodes (external I/O)
        - ModelContractOrchestrator: Contract for ORCHESTRATOR nodes (workflow)
        - ModelContractReducer: Contract for REDUCER nodes (state management)

    Configuration Models:
        Models for configuring various aspects of node behavior.
        - ModelCachingConfig: Caching behavior configuration
        - ModelRetryConfig: Retry policy configuration
        - ModelPerformanceRequirements: Performance SLA definitions
        - ModelValidationRules: Input/output validation rules

    Workflow Models:
        Models for defining and managing workflows.
        - ModelWorkflowConfig: Workflow orchestration configuration
        - ModelWorkflowStep: Individual workflow step definition
        - ModelWorkflowCondition: Conditional execution rules

    Subcontracts:
        Reusable contract components imported from the subcontracts subpackage.

Example:
    Creating a basic contract meta:

    >>> from uuid import uuid4
    >>> from omnibase_core.enums import EnumNodeKind
    >>> from omnibase_core.models.contracts import ModelContractMeta
    >>> meta = ModelContractMeta(
    ...     node_id=uuid4(),
    ...     node_kind=EnumNodeKind.COMPUTE,
    ...     version="1.0.0",
    ...     name="DataTransformer",
    ...     description="Transforms input data format",
    ...     input_schema="omnibase_core.models.ModelInput",
    ...     output_schema="omnibase_core.models.ModelOutput",
    ... )

See Also:
    - CONTRACT_STABILITY_SPEC.md: Detailed specification for contract stability
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md: Architecture overview
"""

from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
from omnibase_core.models.core.model_workflow import ModelWorkflow
from omnibase_core.models.discovery.model_event_descriptor import ModelEventDescriptor
from omnibase_core.models.security.model_condition_value import ModelConditionValue
from omnibase_core.models.services.model_external_service_config import (
    ModelExternalServiceConfig,
)

from . import subcontracts
from .model_action_config_parameter import (
    ModelActionConfigParameter,
    ParameterType,
)
from .model_action_emission_config import ModelActionEmissionConfig
from .model_algorithm_config import ModelAlgorithmConfig
from .model_algorithm_factor_config import ModelAlgorithmFactorConfig
from .model_backup_config import ModelBackupConfig
from .model_branching_config import ModelBranchingConfig
from .model_caching_config import ModelCachingConfig
from .model_compensation_plan import ModelCompensationPlan
from .model_condition_value_list import ModelConditionValueList
from .model_conflict_resolution_config import ModelConflictResolutionConfig
from .model_contract_base import ModelContractBase
from .model_contract_compute import ModelContractCompute
from .model_contract_effect import ModelContractEffect
from .model_contract_fingerprint import ModelContractFingerprint
from .model_contract_meta import (
    ModelContractMeta,
    is_valid_meta_model,
    validate_meta_model,
)
from .model_contract_node_metadata import ModelContractNodeMetadata
from .model_contract_normalization_config import ModelContractNormalizationConfig
from .model_contract_orchestrator import ModelContractOrchestrator
from .model_contract_reducer import ModelContractReducer
from .model_contract_version import ModelContractVersion
from .model_dependency import ModelDependency
from .model_drift_details import ModelDriftDetails
from .model_drift_result import ModelDriftResult
from .model_effect_retry_config import ModelEffectRetryConfig
from .model_event_coordination_config import ModelEventCoordinationConfig
from .model_event_registry_config import ModelEventRegistryConfig
from .model_event_subscription import ModelEventSubscription
from .model_filter_conditions import ModelFilterConditions
from .model_input_validation_config import ModelInputValidationConfig
from .model_io_operation_config import ModelIOOperationConfig
from .model_lifecycle_config import ModelLifecycleConfig
from .model_memory_management_config import ModelMemoryManagementConfig
from .model_node_extensions import ModelNodeExtensions
from .model_node_ref import ModelNodeRef
from .model_output_transformation_config import ModelOutputTransformationConfig
from .model_parallel_config import ModelParallelConfig
from .model_performance_requirements import ModelPerformanceRequirements
from .model_reduction_config import ModelReductionConfig
from .model_runtime_event_bus_config import ModelRuntimeEventBusConfig
from .model_runtime_handler_config import ModelRuntimeHandlerConfig
from .model_runtime_host_contract import ModelRuntimeHostContract
from .model_streaming_config import ModelStreamingConfig
from .model_transaction_config import ModelTransactionConfig
from .model_trigger_mappings import ModelTriggerMappings
from .model_validation_rules import ModelValidationRules
from .model_workflow_condition import ModelWorkflowCondition
from .model_workflow_conditions import ModelWorkflowConditions
from .model_workflow_config import ModelWorkflowConfig
from .model_workflow_dependency import ModelWorkflowDependency
from .model_workflow_step import ModelWorkflowStep

__all__ = [
    # Mixins
    "MixinNodeTypeValidator",
    # Foundation models
    "ModelContractBase",
    "ModelContractFingerprint",
    "ModelContractMeta",
    "ModelContractNodeMetadata",
    "ModelContractNormalizationConfig",
    "ModelContractVersion",
    "ModelDependency",
    "ModelDriftDetails",
    "ModelDriftResult",
    "ModelNodeExtensions",
    "ModelNodeRef",
    "is_valid_meta_model",
    "validate_meta_model",
    # Primary contract models
    "ModelContractCompute",
    "ModelContractEffect",
    "ModelContractOrchestrator",
    "ModelContractReducer",
    # Runtime Host Contract models
    "ModelRuntimeHostContract",
    # Configuration models
    "ModelActionConfigParameter",
    "ParameterType",
    "ModelAlgorithmConfig",
    "ModelAlgorithmFactorConfig",
    "ModelBackupConfig",
    "ModelBranchingConfig",
    "ModelCachingConfig",
    "ModelConflictResolutionConfig",
    "ModelEffectRetryConfig",
    "ModelRuntimeEventBusConfig",
    "ModelEventCoordinationConfig",
    "ModelEventDescriptor",
    "ModelEventRegistryConfig",
    "ModelEventSubscription",
    "ModelExternalServiceConfig",
    "ModelRuntimeHandlerConfig",
    "ModelInputValidationConfig",
    "ModelIOOperationConfig",
    "ModelLifecycleConfig",
    "ModelOutputTransformationConfig",
    "ModelParallelConfig",
    "ModelMemoryManagementConfig",
    "ModelPerformanceRequirements",
    "ModelReductionConfig",
    "ModelStreamingConfig",
    "ModelActionEmissionConfig",
    "ModelTransactionConfig",
    "ModelValidationRules",
    # Workflow models
    "ModelConditionValue",
    "ModelConditionValueList",
    "ModelWorkflowCondition",
    "ModelWorkflowConfig",
    "ModelWorkflowDependency",
    # Orchestrator dependency models
    "ModelCompensationPlan",
    "ModelFilterConditions",
    "ModelTriggerMappings",
    "ModelWorkflowConditions",
    "ModelWorkflowStep",
    # Subcontracts
    "subcontracts",
]
