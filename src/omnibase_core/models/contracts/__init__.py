# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract Models for ONEX Four-Node Architecture.

Pydantic models for validating and managing contract
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

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
    from omnibase_core.models.discovery.model_event_descriptor import (
        ModelEventDescriptor,
    )
    from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
        ModelDescriptorCircuitBreaker,
    )
    from omnibase_core.models.runtime.model_descriptor_retry_policy import (
        ModelDescriptorRetryPolicy,
    )
    from omnibase_core.models.runtime.model_handler_behavior import (
        ModelHandlerBehavior,
    )
    from omnibase_core.models.security.model_condition_value import ModelConditionValue

    from . import subcontracts
    from .evidence import (
        EnumStableProofKind,
        ModelContractEvidenceProof,
        ModelContractEvidenceSpec,
        ModelEvidenceProvenance,
    )
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
    from .model_canonical_topic import ModelCanonicalTopic
    from .model_capability_provided import ModelCapabilityProvided
    from .model_cli_contribution import (
        CLI_CONTRIBUTION_CONTRACT_TYPE,
        ModelCliCommandEntry,
        ModelCliCommandExample,
        ModelCliContribution,
        ModelCliInvocation,
    )
    from .model_compensation_plan import ModelCompensationPlan
    from .model_concurrency_contract_spec import ModelConcurrencyContractSpec
    from .model_condition_value_list import ModelConditionValueList
    from .model_conflict_resolution_config import ModelConflictResolutionConfig
    from .model_consumed_event_entry import ModelConsumedEventEntry
    from .model_contract_base import ModelContractBase
    from .model_contract_compute import ModelContractCompute
    from .model_contract_config import ModelContractConfig
    from .model_contract_effect import ModelContractEffect
    from .model_contract_execution_graph import ModelContractExecutionGraph
    from .model_contract_fingerprint import ModelContractFingerprint
    from .model_contract_meta import (
        ModelContractMeta,
        is_valid_meta_model,
        validate_meta_model,
    )
    from .model_contract_node_metadata import ModelContractNodeMetadata
    from .model_contract_normalization_config import ModelContractNormalizationConfig
    from .model_contract_orchestrator import ModelContractOrchestrator
    from .model_contract_patch import ModelContractPatch
    from .model_contract_reducer import ModelContractReducer
    from .model_contract_version import ModelContractVersion
    from .model_contract_workflow_definition import ModelContractWorkflowDefinition
    from .model_contract_workflow_metadata import ModelContractWorkflowMetadata
    from .model_contract_workflow_node import ModelContractWorkflowNode
    from .model_corpus_classification import ModelCorpusClassification

    # Database repository contract models (OMN-1782)
    from .model_db_operation import ModelDbOperation

    # Database ownership metadata (OMN-2150)
    from .model_db_ownership_metadata import (
        DB_METADATA_CREATE_SQL,
        DB_METADATA_INSERT_SQL,
        DB_METADATA_QUERY_SQL,
        ModelDbOwnershipMetadata,
    )
    from .model_db_param import ModelDbParam
    from .model_db_repository_contract import ModelDbRepositoryContract
    from .model_db_return import ModelDbReturn
    from .model_db_safety_policy import ModelDbSafetyPolicy
    from .model_delegation_dashboard_connection import (
        ModelDelegationDashboardConnection,
    )
    from .model_delegation_datastore import ModelDelegationDatastore
    from .model_delegation_event_bus_endpoint import ModelDelegationEventBusEndpoint
    from .model_delegation_llm_backend import ModelDelegationLlmBackend
    from .model_delegation_pricing_manifest_ref import ModelDelegationPricingManifestRef
    from .model_delegation_projection_api import ModelDelegationProjectionApi
    from .model_delegation_runtime_profile import ModelDelegationRuntimeProfile
    from .model_delegation_secret_ref import ModelDelegationSecretRef
    from .model_delegation_security import ModelDelegationSecurity
    from .model_dependency import ModelDependency
    from .model_dependency_spec import (
        DependencyType,
        ModelDependencySpec,
        SelectionStrategy,
    )
    from .model_descriptor_patch import ModelDescriptorPatch
    from .model_drift_details import ModelDriftDetails
    from .model_drift_result import ModelDriftResult
    from .model_effect_retry_config import ModelEffectRetryConfig
    from .model_event_coordination_config import ModelEventCoordinationConfig
    from .model_event_registry_config import ModelEventRegistryConfig
    from .model_event_subscription import ModelEventSubscription
    from .model_execution_ordering_policy import ModelExecutionOrderingPolicy
    from .model_execution_profile import DEFAULT_EXECUTION_PHASES, ModelExecutionProfile
    from .model_filter_conditions import ModelFilterConditions
    from .model_handler_lifecycle_contract import ModelHandlerLifecycleContract
    from .model_handler_spec import ModelHandlerSpec

    # HTTP wire contracts (OMN-4222)
    from .model_http_request_contract import ModelHttpRequestContract
    from .model_http_response_contract import ModelHttpResponseContract
    from .model_input_validation_config import ModelInputValidationConfig
    from .model_io_operation_config import ModelIOOperationConfig
    from .model_lifecycle_config import ModelLifecycleConfig
    from .model_llm_endpoint_config import ModelLlmEndpointConfig
    from .model_memory_management_config import ModelMemoryManagementConfig
    from .model_node_extensions import ModelNodeExtensions
    from .model_node_ref import ModelNodeRef
    from .model_omnimemory_contract import ModelOmniMemoryContract
    from .model_operational_config import ModelOperationalConfig
    from .model_output_transformation_config import ModelOutputTransformationConfig
    from .model_parallel_config import ModelParallelConfig
    from .model_performance_requirements import ModelPerformanceRequirements
    from .model_profile_reference import ModelProfileReference
    from .model_provenance_decision_record import (
        DecisionRecord,
        ModelProvenanceDecisionRecord,
    )
    from .model_provenance_decision_score import (
        DecisionScore,
        ModelProvenanceDecisionScore,
    )
    from .model_published_event_entry import ModelPublishedEventEntry
    from .model_reduction_config import ModelReductionConfig
    from .model_retry_policy_contract import ModelRetryPolicyContract
    from .model_runtime_event_bus_config import ModelRuntimeEventBusConfig
    from .model_runtime_handler_config import ModelRuntimeHandlerConfig
    from .model_runtime_host_contract import ModelRuntimeHostContract
    from .model_storage_config import ModelStorageConfig
    from .model_streaming_config import ModelStreamingConfig
    from .model_topic_migration_contract import ModelTopicMigrationContract
    from .model_topic_schema_binding import (
        ModelTopicSchemaBinding,
        build_versioned_topic,
        detect_breaking_delta,
        parse_canonical_topic,
    )
    from .model_transaction_config import ModelTransactionConfig
    from .model_trigger_mappings import ModelTriggerMappings
    from .model_validation_rules import ModelValidationRules
    from .model_workflow_condition import ModelWorkflowCondition
    from .model_workflow_conditions import ModelWorkflowConditions
    from .model_workflow_config import ModelWorkflowConfig
    from .model_workflow_dependency import ModelWorkflowDependency
    from .model_workflow_step import ModelWorkflowStep
    from .subcontracts import (
        ModelDbOwnershipSubcontract,
        ModelDbTableDeclaration,
        ModelHandlerRoutingEntry,
        ModelHandlerRoutingSubcontract,
    )

__all__ = [
    # Mixins
    "MixinNodeTypeValidator",
    # Foundation models
    "ModelConsumedEventEntry",
    "ModelContractBase",
    "ModelContractConfig",
    "ModelLlmEndpointConfig",
    "ModelOperationalConfig",
    "ModelStorageConfig",
    "ModelContractFingerprint",
    "ModelContractMeta",
    "ModelContractEvidenceProof",
    "ModelContractEvidenceSpec",
    "ModelContractNodeMetadata",
    "ModelContractNormalizationConfig",
    "ModelContractVersion",
    "ModelEvidenceProvenance",
    "ModelCorpusClassification",
    "ModelDependency",
    "ModelDependencySpec",
    "DependencyType",
    "SelectionStrategy",
    "EnumStableProofKind",
    "ModelDriftDetails",
    "ModelDriftResult",
    "ModelNodeExtensions",
    "ModelNodeRef",
    "ModelOmniMemoryContract",
    "ModelProfileReference",
    "ModelPublishedEventEntry",
    "is_valid_meta_model",
    "validate_meta_model",
    # CLI Contribution contract (OMN-2536)
    "CLI_CONTRIBUTION_CONTRACT_TYPE",
    "ModelCliCommandEntry",
    "ModelCliCommandExample",
    "ModelCliContribution",
    "ModelCliInvocation",
    # Primary contract models
    "ModelContractCompute",
    "ModelContractEffect",
    "ModelContractOrchestrator",
    "ModelContractPatch",
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
    "ModelCapabilityProvided",
    "ModelConflictResolutionConfig",
    "ModelEffectRetryConfig",
    "ModelRuntimeEventBusConfig",
    "ModelEventCoordinationConfig",
    "ModelEventDescriptor",
    "ModelExecutionOrderingPolicy",
    "ModelExecutionProfile",
    "DEFAULT_EXECUTION_PHASES",
    # Handler behavior models (for contract-driven execution)
    "ModelHandlerBehavior",
    "ModelDescriptorPatch",
    "ModelDescriptorRetryPolicy",
    "ModelDescriptorCircuitBreaker",
    "ModelEventRegistryConfig",
    "ModelEventSubscription",
    # NOTE: ModelExternalServiceConfig removed - import from omnibase_core.models.services
    # Handler lifecycle contract (OMN-4221)
    "ModelHandlerLifecycleContract",
    "ModelRetryPolicyContract",
    "ModelHandlerSpec",
    "ModelRuntimeHandlerConfig",
    "ModelInputValidationConfig",
    "ModelIOOperationConfig",
    "ModelLifecycleConfig",
    "ModelOutputTransformationConfig",
    "ModelParallelConfig",
    "ModelMemoryManagementConfig",
    "ModelConcurrencyContractSpec",
    "ModelPerformanceRequirements",
    "ModelReductionConfig",
    "ModelStreamingConfig",
    "ModelActionEmissionConfig",
    "ModelTopicMigrationContract",
    "ModelTopicSchemaBinding",
    "ModelCanonicalTopic",
    "build_versioned_topic",
    "detect_breaking_delta",
    "parse_canonical_topic",
    "ModelTransactionConfig",
    "ModelValidationRules",
    # Workflow models
    "ModelConditionValue",
    "ModelConditionValueList",
    "ModelWorkflowCondition",
    "ModelContractExecutionGraph",
    "ModelContractWorkflowDefinition",
    "ModelContractWorkflowMetadata",
    "ModelContractWorkflowNode",
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
    # Database repository contract models (OMN-1782)
    "ModelDbOperation",
    "ModelDbParam",
    "ModelDbRepositoryContract",
    "ModelDbReturn",
    "ModelDbSafetyPolicy",
    # Database ownership metadata (OMN-2150)
    "ModelDbOwnershipMetadata",
    "DB_METADATA_CREATE_SQL",
    "DB_METADATA_INSERT_SQL",
    "DB_METADATA_QUERY_SQL",
    # DB ownership subcontract (OMN-7916)
    "ModelDbTableDeclaration",
    "ModelDbOwnershipSubcontract",
    # Handler routing models (OMN-1295)
    "ModelHandlerRoutingEntry",
    "ModelHandlerRoutingSubcontract",
    # Decision Provenance models (OMN-2350)
    "ModelProvenanceDecisionScore",
    "ModelProvenanceDecisionRecord",
    "DecisionScore",
    "DecisionRecord",
    # HTTP wire contracts (OMN-4222)
    "ModelHttpRequestContract",
    "ModelHttpResponseContract",
    # Delegation runtime profile contract models (OMN-10919)
    "ModelDelegationRuntimeProfile",
    "ModelDelegationEventBusEndpoint",
    "ModelDelegationLlmBackend",
    "ModelDelegationSecretRef",
    "ModelDelegationSecurity",
    "ModelDelegationPricingManifestRef",
    "ModelDelegationProjectionApi",
    "ModelDelegationDashboardConnection",
    "ModelDelegationDatastore",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "MixinNodeTypeValidator": (
        "omnibase_core.mixins.mixin_node_type_validator",
        "MixinNodeTypeValidator",
    ),
    "ModelEventDescriptor": (
        "omnibase_core.models.discovery.model_event_descriptor",
        "ModelEventDescriptor",
    ),
    "ModelDescriptorCircuitBreaker": (
        "omnibase_core.models.runtime.model_descriptor_circuit_breaker",
        "ModelDescriptorCircuitBreaker",
    ),
    "ModelDescriptorRetryPolicy": (
        "omnibase_core.models.runtime.model_descriptor_retry_policy",
        "ModelDescriptorRetryPolicy",
    ),
    "ModelHandlerBehavior": (
        "omnibase_core.models.runtime.model_handler_behavior",
        "ModelHandlerBehavior",
    ),
    "ModelConditionValue": (
        "omnibase_core.models.security.model_condition_value",
        "ModelConditionValue",
    ),
    "subcontracts": ("omnibase_core.models.contracts.subcontracts", None),
    "EnumStableProofKind": (
        "omnibase_core.models.contracts.evidence",
        "EnumStableProofKind",
    ),
    "ModelContractEvidenceProof": (
        "omnibase_core.models.contracts.evidence",
        "ModelContractEvidenceProof",
    ),
    "ModelContractEvidenceSpec": (
        "omnibase_core.models.contracts.evidence",
        "ModelContractEvidenceSpec",
    ),
    "ModelEvidenceProvenance": (
        "omnibase_core.models.contracts.evidence",
        "ModelEvidenceProvenance",
    ),
    "ModelActionConfigParameter": (
        "omnibase_core.models.contracts.model_action_config_parameter",
        "ModelActionConfigParameter",
    ),
    "ParameterType": (
        "omnibase_core.models.contracts.model_action_config_parameter",
        "ParameterType",
    ),
    "ModelActionEmissionConfig": (
        "omnibase_core.models.contracts.model_action_emission_config",
        "ModelActionEmissionConfig",
    ),
    "ModelAlgorithmConfig": (
        "omnibase_core.models.contracts.model_algorithm_config",
        "ModelAlgorithmConfig",
    ),
    "ModelAlgorithmFactorConfig": (
        "omnibase_core.models.contracts.model_algorithm_factor_config",
        "ModelAlgorithmFactorConfig",
    ),
    "ModelBackupConfig": (
        "omnibase_core.models.contracts.model_backup_config",
        "ModelBackupConfig",
    ),
    "ModelBranchingConfig": (
        "omnibase_core.models.contracts.model_branching_config",
        "ModelBranchingConfig",
    ),
    "ModelCachingConfig": (
        "omnibase_core.models.contracts.model_caching_config",
        "ModelCachingConfig",
    ),
    "ModelCanonicalTopic": (
        "omnibase_core.models.contracts.model_canonical_topic",
        "ModelCanonicalTopic",
    ),
    "ModelCapabilityProvided": (
        "omnibase_core.models.contracts.model_capability_provided",
        "ModelCapabilityProvided",
    ),
    "CLI_CONTRIBUTION_CONTRACT_TYPE": (
        "omnibase_core.models.contracts.model_cli_contribution",
        "CLI_CONTRIBUTION_CONTRACT_TYPE",
    ),
    "ModelCliCommandEntry": (
        "omnibase_core.models.contracts.model_cli_contribution",
        "ModelCliCommandEntry",
    ),
    "ModelCliCommandExample": (
        "omnibase_core.models.contracts.model_cli_contribution",
        "ModelCliCommandExample",
    ),
    "ModelCliContribution": (
        "omnibase_core.models.contracts.model_cli_contribution",
        "ModelCliContribution",
    ),
    "ModelCliInvocation": (
        "omnibase_core.models.contracts.model_cli_contribution",
        "ModelCliInvocation",
    ),
    "ModelCompensationPlan": (
        "omnibase_core.models.contracts.model_compensation_plan",
        "ModelCompensationPlan",
    ),
    "ModelConcurrencyContractSpec": (
        "omnibase_core.models.contracts.model_concurrency_contract_spec",
        "ModelConcurrencyContractSpec",
    ),
    "ModelConditionValueList": (
        "omnibase_core.models.contracts.model_condition_value_list",
        "ModelConditionValueList",
    ),
    "ModelConflictResolutionConfig": (
        "omnibase_core.models.contracts.model_conflict_resolution_config",
        "ModelConflictResolutionConfig",
    ),
    "ModelConsumedEventEntry": (
        "omnibase_core.models.contracts.model_consumed_event_entry",
        "ModelConsumedEventEntry",
    ),
    "ModelContractBase": (
        "omnibase_core.models.contracts.model_contract_base",
        "ModelContractBase",
    ),
    "ModelContractCompute": (
        "omnibase_core.models.contracts.model_contract_compute",
        "ModelContractCompute",
    ),
    "ModelContractConfig": (
        "omnibase_core.models.contracts.model_contract_config",
        "ModelContractConfig",
    ),
    "ModelContractEffect": (
        "omnibase_core.models.contracts.model_contract_effect",
        "ModelContractEffect",
    ),
    "ModelContractExecutionGraph": (
        "omnibase_core.models.contracts.model_contract_execution_graph",
        "ModelContractExecutionGraph",
    ),
    "ModelContractFingerprint": (
        "omnibase_core.models.contracts.model_contract_fingerprint",
        "ModelContractFingerprint",
    ),
    "ModelContractMeta": (
        "omnibase_core.models.contracts.model_contract_meta",
        "ModelContractMeta",
    ),
    "is_valid_meta_model": (
        "omnibase_core.models.contracts.model_contract_meta",
        "is_valid_meta_model",
    ),
    "validate_meta_model": (
        "omnibase_core.models.contracts.model_contract_meta",
        "validate_meta_model",
    ),
    "ModelContractNodeMetadata": (
        "omnibase_core.models.contracts.model_contract_node_metadata",
        "ModelContractNodeMetadata",
    ),
    "ModelContractNormalizationConfig": (
        "omnibase_core.models.contracts.model_contract_normalization_config",
        "ModelContractNormalizationConfig",
    ),
    "ModelContractOrchestrator": (
        "omnibase_core.models.contracts.model_contract_orchestrator",
        "ModelContractOrchestrator",
    ),
    "ModelContractPatch": (
        "omnibase_core.models.contracts.model_contract_patch",
        "ModelContractPatch",
    ),
    "ModelContractReducer": (
        "omnibase_core.models.contracts.model_contract_reducer",
        "ModelContractReducer",
    ),
    "ModelContractVersion": (
        "omnibase_core.models.contracts.model_contract_version",
        "ModelContractVersion",
    ),
    "ModelContractWorkflowDefinition": (
        "omnibase_core.models.contracts.model_contract_workflow_definition",
        "ModelContractWorkflowDefinition",
    ),
    "ModelContractWorkflowMetadata": (
        "omnibase_core.models.contracts.model_contract_workflow_metadata",
        "ModelContractWorkflowMetadata",
    ),
    "ModelContractWorkflowNode": (
        "omnibase_core.models.contracts.model_contract_workflow_node",
        "ModelContractWorkflowNode",
    ),
    "ModelCorpusClassification": (
        "omnibase_core.models.contracts.model_corpus_classification",
        "ModelCorpusClassification",
    ),
    "ModelDbOperation": (
        "omnibase_core.models.contracts.model_db_operation",
        "ModelDbOperation",
    ),
    "DB_METADATA_CREATE_SQL": (
        "omnibase_core.models.contracts.model_db_ownership_metadata",
        "DB_METADATA_CREATE_SQL",
    ),
    "DB_METADATA_INSERT_SQL": (
        "omnibase_core.models.contracts.model_db_ownership_metadata",
        "DB_METADATA_INSERT_SQL",
    ),
    "DB_METADATA_QUERY_SQL": (
        "omnibase_core.models.contracts.model_db_ownership_metadata",
        "DB_METADATA_QUERY_SQL",
    ),
    "ModelDbOwnershipMetadata": (
        "omnibase_core.models.contracts.model_db_ownership_metadata",
        "ModelDbOwnershipMetadata",
    ),
    "ModelDbParam": ("omnibase_core.models.contracts.model_db_param", "ModelDbParam"),
    "ModelDbRepositoryContract": (
        "omnibase_core.models.contracts.model_db_repository_contract",
        "ModelDbRepositoryContract",
    ),
    "ModelDbReturn": (
        "omnibase_core.models.contracts.model_db_return",
        "ModelDbReturn",
    ),
    "ModelDbSafetyPolicy": (
        "omnibase_core.models.contracts.model_db_safety_policy",
        "ModelDbSafetyPolicy",
    ),
    "ModelDelegationDashboardConnection": (
        "omnibase_core.models.contracts.model_delegation_dashboard_connection",
        "ModelDelegationDashboardConnection",
    ),
    "ModelDelegationDatastore": (
        "omnibase_core.models.contracts.model_delegation_datastore",
        "ModelDelegationDatastore",
    ),
    "ModelDelegationEventBusEndpoint": (
        "omnibase_core.models.contracts.model_delegation_event_bus_endpoint",
        "ModelDelegationEventBusEndpoint",
    ),
    "ModelDelegationLlmBackend": (
        "omnibase_core.models.contracts.model_delegation_llm_backend",
        "ModelDelegationLlmBackend",
    ),
    "ModelDelegationPricingManifestRef": (
        "omnibase_core.models.contracts.model_delegation_pricing_manifest_ref",
        "ModelDelegationPricingManifestRef",
    ),
    "ModelDelegationProjectionApi": (
        "omnibase_core.models.contracts.model_delegation_projection_api",
        "ModelDelegationProjectionApi",
    ),
    "ModelDelegationRuntimeProfile": (
        "omnibase_core.models.contracts.model_delegation_runtime_profile",
        "ModelDelegationRuntimeProfile",
    ),
    "ModelDelegationSecretRef": (
        "omnibase_core.models.contracts.model_delegation_secret_ref",
        "ModelDelegationSecretRef",
    ),
    "ModelDelegationSecurity": (
        "omnibase_core.models.contracts.model_delegation_security",
        "ModelDelegationSecurity",
    ),
    "ModelDependency": (
        "omnibase_core.models.contracts.model_dependency",
        "ModelDependency",
    ),
    "DependencyType": (
        "omnibase_core.models.contracts.model_dependency_spec",
        "DependencyType",
    ),
    "ModelDependencySpec": (
        "omnibase_core.models.contracts.model_dependency_spec",
        "ModelDependencySpec",
    ),
    "SelectionStrategy": (
        "omnibase_core.models.contracts.model_dependency_spec",
        "SelectionStrategy",
    ),
    "ModelDescriptorPatch": (
        "omnibase_core.models.contracts.model_descriptor_patch",
        "ModelDescriptorPatch",
    ),
    "ModelDriftDetails": (
        "omnibase_core.models.contracts.model_drift_details",
        "ModelDriftDetails",
    ),
    "ModelDriftResult": (
        "omnibase_core.models.contracts.model_drift_result",
        "ModelDriftResult",
    ),
    "ModelEffectRetryConfig": (
        "omnibase_core.models.contracts.model_effect_retry_config",
        "ModelEffectRetryConfig",
    ),
    "ModelEventCoordinationConfig": (
        "omnibase_core.models.contracts.model_event_coordination_config",
        "ModelEventCoordinationConfig",
    ),
    "ModelEventRegistryConfig": (
        "omnibase_core.models.contracts.model_event_registry_config",
        "ModelEventRegistryConfig",
    ),
    "ModelEventSubscription": (
        "omnibase_core.models.contracts.model_event_subscription",
        "ModelEventSubscription",
    ),
    "ModelExecutionOrderingPolicy": (
        "omnibase_core.models.contracts.model_execution_ordering_policy",
        "ModelExecutionOrderingPolicy",
    ),
    "DEFAULT_EXECUTION_PHASES": (
        "omnibase_core.models.contracts.model_execution_profile",
        "DEFAULT_EXECUTION_PHASES",
    ),
    "ModelExecutionProfile": (
        "omnibase_core.models.contracts.model_execution_profile",
        "ModelExecutionProfile",
    ),
    "ModelFilterConditions": (
        "omnibase_core.models.contracts.model_filter_conditions",
        "ModelFilterConditions",
    ),
    "ModelHandlerLifecycleContract": (
        "omnibase_core.models.contracts.model_handler_lifecycle_contract",
        "ModelHandlerLifecycleContract",
    ),
    "ModelHandlerSpec": (
        "omnibase_core.models.contracts.model_handler_spec",
        "ModelHandlerSpec",
    ),
    "ModelHttpRequestContract": (
        "omnibase_core.models.contracts.model_http_request_contract",
        "ModelHttpRequestContract",
    ),
    "ModelHttpResponseContract": (
        "omnibase_core.models.contracts.model_http_response_contract",
        "ModelHttpResponseContract",
    ),
    "ModelInputValidationConfig": (
        "omnibase_core.models.contracts.model_input_validation_config",
        "ModelInputValidationConfig",
    ),
    "ModelIOOperationConfig": (
        "omnibase_core.models.contracts.model_io_operation_config",
        "ModelIOOperationConfig",
    ),
    "ModelLifecycleConfig": (
        "omnibase_core.models.contracts.model_lifecycle_config",
        "ModelLifecycleConfig",
    ),
    "ModelLlmEndpointConfig": (
        "omnibase_core.models.contracts.model_llm_endpoint_config",
        "ModelLlmEndpointConfig",
    ),
    "ModelMemoryManagementConfig": (
        "omnibase_core.models.contracts.model_memory_management_config",
        "ModelMemoryManagementConfig",
    ),
    "ModelNodeExtensions": (
        "omnibase_core.models.contracts.model_node_extensions",
        "ModelNodeExtensions",
    ),
    "ModelNodeRef": ("omnibase_core.models.contracts.model_node_ref", "ModelNodeRef"),
    "ModelOmniMemoryContract": (
        "omnibase_core.models.contracts.model_omnimemory_contract",
        "ModelOmniMemoryContract",
    ),
    "ModelOperationalConfig": (
        "omnibase_core.models.contracts.model_operational_config",
        "ModelOperationalConfig",
    ),
    "ModelOutputTransformationConfig": (
        "omnibase_core.models.contracts.model_output_transformation_config",
        "ModelOutputTransformationConfig",
    ),
    "ModelParallelConfig": (
        "omnibase_core.models.contracts.model_parallel_config",
        "ModelParallelConfig",
    ),
    "ModelPerformanceRequirements": (
        "omnibase_core.models.contracts.model_performance_requirements",
        "ModelPerformanceRequirements",
    ),
    "ModelProfileReference": (
        "omnibase_core.models.contracts.model_profile_reference",
        "ModelProfileReference",
    ),
    "DecisionRecord": (
        "omnibase_core.models.contracts.model_provenance_decision_record",
        "DecisionRecord",
    ),
    "ModelProvenanceDecisionRecord": (
        "omnibase_core.models.contracts.model_provenance_decision_record",
        "ModelProvenanceDecisionRecord",
    ),
    "DecisionScore": (
        "omnibase_core.models.contracts.model_provenance_decision_score",
        "DecisionScore",
    ),
    "ModelProvenanceDecisionScore": (
        "omnibase_core.models.contracts.model_provenance_decision_score",
        "ModelProvenanceDecisionScore",
    ),
    "ModelPublishedEventEntry": (
        "omnibase_core.models.contracts.model_published_event_entry",
        "ModelPublishedEventEntry",
    ),
    "ModelReductionConfig": (
        "omnibase_core.models.contracts.model_reduction_config",
        "ModelReductionConfig",
    ),
    "ModelRetryPolicyContract": (
        "omnibase_core.models.contracts.model_retry_policy_contract",
        "ModelRetryPolicyContract",
    ),
    "ModelRuntimeEventBusConfig": (
        "omnibase_core.models.contracts.model_runtime_event_bus_config",
        "ModelRuntimeEventBusConfig",
    ),
    "ModelRuntimeHandlerConfig": (
        "omnibase_core.models.contracts.model_runtime_handler_config",
        "ModelRuntimeHandlerConfig",
    ),
    "ModelRuntimeHostContract": (
        "omnibase_core.models.contracts.model_runtime_host_contract",
        "ModelRuntimeHostContract",
    ),
    "ModelStorageConfig": (
        "omnibase_core.models.contracts.model_storage_config",
        "ModelStorageConfig",
    ),
    "ModelStreamingConfig": (
        "omnibase_core.models.contracts.model_streaming_config",
        "ModelStreamingConfig",
    ),
    "ModelTopicMigrationContract": (
        "omnibase_core.models.contracts.model_topic_migration_contract",
        "ModelTopicMigrationContract",
    ),
    "ModelTopicSchemaBinding": (
        "omnibase_core.models.contracts.model_topic_schema_binding",
        "ModelTopicSchemaBinding",
    ),
    "build_versioned_topic": (
        "omnibase_core.models.contracts.model_topic_schema_binding",
        "build_versioned_topic",
    ),
    "detect_breaking_delta": (
        "omnibase_core.models.contracts.model_topic_schema_binding",
        "detect_breaking_delta",
    ),
    "parse_canonical_topic": (
        "omnibase_core.models.contracts.model_topic_schema_binding",
        "parse_canonical_topic",
    ),
    "ModelTransactionConfig": (
        "omnibase_core.models.contracts.model_transaction_config",
        "ModelTransactionConfig",
    ),
    "ModelTriggerMappings": (
        "omnibase_core.models.contracts.model_trigger_mappings",
        "ModelTriggerMappings",
    ),
    "ModelValidationRules": (
        "omnibase_core.models.contracts.model_validation_rules",
        "ModelValidationRules",
    ),
    "ModelWorkflowCondition": (
        "omnibase_core.models.contracts.model_workflow_condition",
        "ModelWorkflowCondition",
    ),
    "ModelWorkflowConditions": (
        "omnibase_core.models.contracts.model_workflow_conditions",
        "ModelWorkflowConditions",
    ),
    "ModelWorkflowConfig": (
        "omnibase_core.models.contracts.model_workflow_config",
        "ModelWorkflowConfig",
    ),
    "ModelWorkflowDependency": (
        "omnibase_core.models.contracts.model_workflow_dependency",
        "ModelWorkflowDependency",
    ),
    "ModelWorkflowStep": (
        "omnibase_core.models.contracts.model_workflow_step",
        "ModelWorkflowStep",
    ),
    "ModelDbOwnershipSubcontract": (
        "omnibase_core.models.contracts.subcontracts",
        "ModelDbOwnershipSubcontract",
    ),
    "ModelDbTableDeclaration": (
        "omnibase_core.models.contracts.subcontracts",
        "ModelDbTableDeclaration",
    ),
    "ModelHandlerRoutingEntry": (
        "omnibase_core.models.contracts.subcontracts",
        "ModelHandlerRoutingEntry",
    ),
    "ModelHandlerRoutingSubcontract": (
        "omnibase_core.models.contracts.subcontracts",
        "ModelHandlerRoutingSubcontract",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
