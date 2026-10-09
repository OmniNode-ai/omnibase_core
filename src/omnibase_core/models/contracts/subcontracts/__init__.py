# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Subcontract Models - Contracts Module.

Provides dedicated Pydantic models for all ONEX subcontract patterns:
- Aggregation: Data aggregation patterns and policies
- Caching: Cache strategies, invalidation, and performance tuning
- Configuration: Configuration management and validation
- Discovery: Service discovery and introspection response configuration
- Event Type: Event type definitions and routing
- FSM (Finite State Machine): State machine behavior and transitions
- Lifecycle: Node startup, shutdown, and lifecycle event management
- Routing: Message routing and load balancing strategies
- State Management: State persistence and synchronization
- Tool Execution: Tool execution configuration and behavior
- Workflow Coordination: Multi-step workflow orchestration

These models are composed into node contracts via Union types and optional fields,
providing clean separation between node logic and subcontract functionality.

Strong typing with comprehensive type safety.
"""

from __future__ import annotations

# Re-export constant from canonical location
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.constants import IDEMPOTENCY_DEFAULTS
    from omnibase_core.enums.enum_retrieval_source_type import EnumRetrievalSourceType
    from omnibase_core.models.core.model_health_check_result import (
        ModelHealthCheckResult,
    )
    from omnibase_core.models.core.model_workflow_metrics import ModelWorkflowMetrics
    from omnibase_core.models.fsm.model_fsm_operation import ModelFSMOperation
    from omnibase_core.models.fsm.model_fsm_transition_action import (
        ModelFSMTransitionAction,
    )
    from omnibase_core.models.fsm.model_fsm_transition_condition import (
        ModelFSMTransitionCondition,
    )

    # Subcontract model imports (alphabetical order)
    from .model_aggregation_function import ModelAggregationFunction
    from .model_aggregation_performance import ModelAggregationPerformance
    from .model_aggregation_subcontract import ModelAggregationSubcontract
    from .model_binding_expression import ModelBindingExpression
    from .model_cache_distribution import ModelCacheDistribution
    from .model_cache_invalidation import ModelCacheInvalidation
    from .model_cache_key_strategy import ModelCacheKeyStrategy
    from .model_cache_performance import ModelCachePerformance
    from .model_caching_subcontract import ModelCachingSubcontract
    from .model_circuit_breaker_subcontract import ModelCircuitBreakerSubcontract
    from .model_component_health import ModelComponentHealth
    from .model_component_health_collection import ModelComponentHealthCollection
    from .model_compute_pipeline_step import ModelComputePipelineStep
    from .model_compute_subcontract import ModelComputeSubcontract
    from .model_configuration_source import ModelConfigurationSource
    from .model_configuration_subcontract import ModelConfigurationSubcontract
    from .model_configuration_validation import ModelConfigurationValidation
    from .model_context_integrity_subcontract import ModelContextIntegritySubcontract
    from .model_contract_behavior_spec import ModelContractBehaviorSpec
    from .model_coordination_result import ModelCoordinationResult
    from .model_coordination_rules import ModelCoordinationRules
    from .model_correlation_config import ModelCorrelationConfig
    from .model_data_grouping import ModelDataGrouping
    from .model_db_ownership_subcontract import (
        ModelDbOwnershipSubcontract,
        ModelDbTableDeclaration,
    )
    from .model_dependency_health import ModelDependencyHealth
    from .model_discovery_subcontract import ModelDiscoverySubcontract

    # Effect subcontract imports (Contract-Driven NodeEffect v1.0)
    # Individual model imports from split files
    from .model_effect_circuit_breaker import ModelEffectCircuitBreaker
    from .model_effect_contract_metadata import ModelEffectContractMetadata
    from .model_effect_input_schema import ModelEffectInputSchema

    # Effect IO config imports (Contract-Driven NodeEffect v1.0)
    from .model_effect_io_configs import (
        EffectIOConfig,
        ModelDbIOConfig,
        ModelFilesystemIOConfig,
        ModelHttpIOConfig,
        ModelKafkaIOConfig,
    )
    from .model_effect_observability import ModelEffectObservability
    from .model_effect_operation import ModelEffectOperation
    from .model_effect_operation_result import ModelEffectOperationResult

    # Effect resolved context imports (Contract-Driven NodeEffect v1.0)
    from .model_effect_resolved_context import ResolvedIOContext
    from .model_effect_response_handling import ModelEffectResponseHandling
    from .model_effect_retry_policy import ModelEffectRetryPolicy
    from .model_effect_subcontract import ModelEffectSubcontract
    from .model_effect_transaction_config import ModelEffectTransactionConfig
    from .model_envelope_template import ModelEnvelopeTemplate
    from .model_event_bus_subcontract import ModelEventBusSubcontract
    from .model_event_definition import ModelEventDefinition
    from .model_event_handling_subcontract import ModelEventHandlingSubcontract
    from .model_event_persistence import ModelEventPersistence
    from .model_event_routing import ModelEventRouting
    from .model_event_transformation import ModelEventTransformation
    from .model_event_type_subcontract import ModelEventTypeSubcontract
    from .model_execution_graph import ModelExecutionGraph
    from .model_fsm_state_definition import ModelFSMStateDefinition
    from .model_fsm_state_transition import ModelFSMStateTransition
    from .model_fsm_subcontract import ModelFSMSubcontract
    from .model_handler_routing_entry import ModelHandlerRoutingEntry
    from .model_handler_routing_subcontract import ModelHandlerRoutingSubcontract
    from .model_health_check_subcontract import ModelHealthCheckSubcontract
    from .model_hook_activation import ModelHookActivation
    from .model_introspection_subcontract import ModelIntrospectionSubcontract
    from .model_lifecycle_subcontract import ModelLifecycleSubcontract
    from .model_load_balancing import ModelLoadBalancing
    from .model_logging_subcontract import ModelLoggingSubcontract
    from .model_metrics_subcontract import ModelMetricsSubcontract
    from .model_node_assignment import ModelNodeAssignment
    from .model_node_health_status import ModelNodeHealthStatus
    from .model_node_progress import ModelNodeProgress
    from .model_observability_subcontract import ModelObservabilitySubcontract
    from .model_operation_bindings import ModelOperationBindings
    from .model_operation_mapping import ModelOperationMapping
    from .model_package_hook_activations import ModelPackageHookActivations
    from .model_progress_status import ModelProgressStatus
    from .model_protocol_dependency import ModelProtocolDependency
    from .model_reply_topics import ModelReplyTopics
    from .model_request_response_config import ModelRequestResponseConfig
    from .model_request_response_instance import ModelRequestResponseInstance
    from .model_request_transformation import ModelRequestTransformation
    from .model_resolved_db_context import ModelResolvedDbContext
    from .model_resolved_filesystem_context import ModelResolvedFilesystemContext
    from .model_resolved_http_context import ModelResolvedHttpContext
    from .model_resolved_kafka_context import ModelResolvedKafkaContext
    from .model_response_mapping import ModelResponseMapping
    from .model_retrieval_source import ModelRetrievalSource
    from .model_retry_subcontract import ModelRetrySubcontract
    from .model_return_schema import ModelReturnSchema
    from .model_route_definition import ModelRouteDefinition
    from .model_routing_metrics import ModelRoutingMetrics
    from .model_routing_subcontract import ModelRoutingSubcontract
    from .model_runtime_lane_scope import ModelRuntimeLaneScope
    from .model_security_subcontract import ModelSecuritySubcontract
    from .model_serialization_subcontract import ModelSerializationSubcontract
    from .model_state_management_subcontract import ModelStateManagementSubcontract
    from .model_state_persistence import ModelStatePersistence
    from .model_state_synchronization import ModelStateSynchronization
    from .model_state_validation import ModelStateValidation
    from .model_state_versioning import ModelStateVersioning
    from .model_statistical_computation import ModelStatisticalComputation
    from .model_synchronization_point import ModelSynchronizationPoint
    from .model_tool_execution_subcontract import ModelToolExecutionSubcontract
    from .model_topic_meta import ModelTopicMeta
    from .model_topic_provisioning_config import ModelTopicProvisioningConfig
    from .model_validation_subcontract import ModelValidationSubcontract
    from .model_validator_rule import ModelValidatorRule
    from .model_validator_subcontract import ModelValidatorSubcontract
    from .model_windowing_strategy import ModelWindowingStrategy
    from .model_workflow_coordination_subcontract import (
        ModelWorkflowCoordinationSubcontract,
    )
    from .model_workflow_definition import ModelWorkflowDefinition
    from .model_workflow_definition_metadata import ModelWorkflowDefinitionMetadata
    from .model_workflow_instance import ModelWorkflowInstance
    from .model_workflow_node import ModelWorkflowNode

__all__ = [
    # Effect IO config models (Contract-Driven NodeEffect v1.0)
    "ModelHttpIOConfig",
    "ModelDbIOConfig",
    "ModelKafkaIOConfig",
    "ModelFilesystemIOConfig",
    "EffectIOConfig",
    # Effect resolved context models (Contract-Driven NodeEffect v1.0)
    "ModelResolvedHttpContext",
    "ModelResolvedDbContext",
    "ModelResolvedKafkaContext",
    "ModelResolvedFilesystemContext",
    "ResolvedIOContext",
    # Effect subcontract models (Contract-Driven NodeEffect v1.0)
    "ModelEffectRetryPolicy",
    "IDEMPOTENCY_DEFAULTS",
    "ModelEffectCircuitBreaker",
    "ModelEffectTransactionConfig",
    "ModelEffectResponseHandling",
    "ModelEffectObservability",
    "ModelEffectOperation",
    "ModelEffectOperationResult",
    "ModelEffectContractMetadata",
    "ModelEffectInputSchema",
    "ModelEffectSubcontract",
    # Aggregation subcontracts and components
    "ModelAggregationSubcontract",
    "ModelAggregationFunction",
    "ModelAggregationPerformance",
    "ModelDataGrouping",
    "ModelStatisticalComputation",
    "ModelWindowingStrategy",
    # Binding expression models (Operation Bindings DSL)
    "ModelBindingExpression",
    "ModelEnvelopeTemplate",
    "ModelOperationBindings",
    "ModelOperationMapping",
    "ModelResponseMapping",
    # Caching subcontracts and components
    "ModelCachingSubcontract",
    "ModelCacheDistribution",
    "ModelCacheInvalidation",
    "ModelCacheKeyStrategy",
    "ModelCachePerformance",
    # Behavioral execution profile (first slice of ModelContractBase decomposition)
    "ModelContractBehaviorSpec",
    # Circuit breaker subcontracts
    "ModelCircuitBreakerSubcontract",
    # Compute subcontracts and components
    "ModelComputePipelineStep",
    "ModelComputeSubcontract",
    # Context integrity subcontracts and components
    "EnumRetrievalSourceType",
    "ModelContextIntegritySubcontract",
    "ModelRetrievalSource",
    "ModelReturnSchema",
    # Configuration subcontracts and components
    "ModelConfigurationSubcontract",
    "ModelConfigurationSource",
    "ModelConfigurationValidation",
    # DB ownership subcontracts (OMN-7916)
    "ModelDbTableDeclaration",
    "ModelDbOwnershipSubcontract",
    # Runtime lane scope (OMN-19408)
    "ModelRuntimeLaneScope",
    # Discovery subcontracts
    "ModelDiscoverySubcontract",
    # Event type subcontracts and components
    "ModelEventTypeSubcontract",
    "ModelEventBusSubcontract",
    "ModelEventDefinition",
    "ModelEventHandlingSubcontract",
    "ModelEventPersistence",
    "ModelEventRouting",
    "ModelEventTransformation",
    "ModelCorrelationConfig",
    "ModelReplyTopics",
    "ModelRequestResponseConfig",
    "ModelRequestResponseInstance",
    "ModelTopicMeta",
    "ModelTopicProvisioningConfig",
    # FSM subcontracts and components
    "ModelFSMSubcontract",
    "ModelFSMOperation",
    "ModelFSMStateDefinition",
    "ModelFSMStateTransition",
    "ModelFSMTransitionAction",
    "ModelFSMTransitionCondition",
    # Handler routing subcontracts and components
    "ModelHandlerRoutingEntry",
    "ModelHandlerRoutingSubcontract",
    # Health check subcontracts and components
    "ModelComponentHealth",
    "ModelComponentHealthCollection",
    "ModelDependencyHealth",
    "ModelHealthCheckResult",
    "ModelHealthCheckSubcontract",
    "ModelHookActivation",
    "ModelPackageHookActivations",
    "ModelNodeHealthStatus",
    # Introspection subcontracts
    "ModelIntrospectionSubcontract",
    # Lifecycle subcontracts
    "ModelLifecycleSubcontract",
    # Logging subcontracts
    "ModelLoggingSubcontract",
    # Metrics subcontracts
    "ModelMetricsSubcontract",
    # Observability subcontracts
    "ModelObservabilitySubcontract",
    # Protocol dependency subcontracts (Contract-Driven DI)
    "ModelProtocolDependency",
    # Retry subcontracts
    "ModelRetrySubcontract",
    # Routing subcontracts and components
    "ModelRoutingSubcontract",
    "ModelLoadBalancing",
    "ModelRequestTransformation",
    "ModelRouteDefinition",
    "ModelRoutingMetrics",
    # Security subcontracts
    "ModelSecuritySubcontract",
    # Serialization subcontracts
    "ModelSerializationSubcontract",
    # State management subcontracts and components
    "ModelStateManagementSubcontract",
    "ModelStatePersistence",
    "ModelStateSynchronization",
    "ModelStateValidation",
    "ModelStateVersioning",
    # Tool execution subcontracts
    "ModelToolExecutionSubcontract",
    # Validation subcontracts (Pydantic validation behavior)
    "ModelValidationSubcontract",
    # Validator subcontracts (file-based validators)
    "ModelValidatorRule",
    "ModelValidatorSubcontract",
    # Workflow coordination subcontracts and components
    "ModelWorkflowCoordinationSubcontract",
    "ModelCoordinationResult",
    "ModelCoordinationRules",
    "ModelExecutionGraph",
    "ModelNodeAssignment",
    "ModelNodeProgress",
    "ModelProgressStatus",
    "ModelSynchronizationPoint",
    "ModelWorkflowDefinition",
    "ModelWorkflowInstance",
    "ModelWorkflowDefinitionMetadata",
    "ModelWorkflowMetrics",
    "ModelWorkflowNode",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "IDEMPOTENCY_DEFAULTS": ("omnibase_core.constants", "IDEMPOTENCY_DEFAULTS"),
    "EnumRetrievalSourceType": (
        "omnibase_core.enums.enum_retrieval_source_type",
        "EnumRetrievalSourceType",
    ),
    "ModelHealthCheckResult": (
        "omnibase_core.models.core.model_health_check_result",
        "ModelHealthCheckResult",
    ),
    "ModelWorkflowMetrics": (
        "omnibase_core.models.core.model_workflow_metrics",
        "ModelWorkflowMetrics",
    ),
    "ModelFSMOperation": (
        "omnibase_core.models.fsm.model_fsm_operation",
        "ModelFSMOperation",
    ),
    "ModelFSMTransitionAction": (
        "omnibase_core.models.fsm.model_fsm_transition_action",
        "ModelFSMTransitionAction",
    ),
    "ModelFSMTransitionCondition": (
        "omnibase_core.models.fsm.model_fsm_transition_condition",
        "ModelFSMTransitionCondition",
    ),
    "ModelAggregationFunction": (
        "omnibase_core.models.contracts.subcontracts.model_aggregation_function",
        "ModelAggregationFunction",
    ),
    "ModelAggregationPerformance": (
        "omnibase_core.models.contracts.subcontracts.model_aggregation_performance",
        "ModelAggregationPerformance",
    ),
    "ModelAggregationSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_aggregation_subcontract",
        "ModelAggregationSubcontract",
    ),
    "ModelBindingExpression": (
        "omnibase_core.models.contracts.subcontracts.model_binding_expression",
        "ModelBindingExpression",
    ),
    "ModelCacheDistribution": (
        "omnibase_core.models.contracts.subcontracts.model_cache_distribution",
        "ModelCacheDistribution",
    ),
    "ModelCacheInvalidation": (
        "omnibase_core.models.contracts.subcontracts.model_cache_invalidation",
        "ModelCacheInvalidation",
    ),
    "ModelCacheKeyStrategy": (
        "omnibase_core.models.contracts.subcontracts.model_cache_key_strategy",
        "ModelCacheKeyStrategy",
    ),
    "ModelCachePerformance": (
        "omnibase_core.models.contracts.subcontracts.model_cache_performance",
        "ModelCachePerformance",
    ),
    "ModelCachingSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_caching_subcontract",
        "ModelCachingSubcontract",
    ),
    "ModelCircuitBreakerSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_circuit_breaker_subcontract",
        "ModelCircuitBreakerSubcontract",
    ),
    "ModelComponentHealth": (
        "omnibase_core.models.contracts.subcontracts.model_component_health",
        "ModelComponentHealth",
    ),
    "ModelComponentHealthCollection": (
        "omnibase_core.models.contracts.subcontracts.model_component_health_collection",
        "ModelComponentHealthCollection",
    ),
    "ModelComputePipelineStep": (
        "omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step",
        "ModelComputePipelineStep",
    ),
    "ModelComputeSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_compute_subcontract",
        "ModelComputeSubcontract",
    ),
    "ModelConfigurationSource": (
        "omnibase_core.models.contracts.subcontracts.model_configuration_source",
        "ModelConfigurationSource",
    ),
    "ModelConfigurationSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_configuration_subcontract",
        "ModelConfigurationSubcontract",
    ),
    "ModelConfigurationValidation": (
        "omnibase_core.models.contracts.subcontracts.model_configuration_validation",
        "ModelConfigurationValidation",
    ),
    "ModelContextIntegritySubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_context_integrity_subcontract",
        "ModelContextIntegritySubcontract",
    ),
    "ModelContractBehaviorSpec": (
        "omnibase_core.models.contracts.subcontracts.model_contract_behavior_spec",
        "ModelContractBehaviorSpec",
    ),
    "ModelCoordinationResult": (
        "omnibase_core.models.contracts.subcontracts.model_coordination_result",
        "ModelCoordinationResult",
    ),
    "ModelCoordinationRules": (
        "omnibase_core.models.contracts.subcontracts.model_coordination_rules",
        "ModelCoordinationRules",
    ),
    "ModelCorrelationConfig": (
        "omnibase_core.models.contracts.subcontracts.model_correlation_config",
        "ModelCorrelationConfig",
    ),
    "ModelDataGrouping": (
        "omnibase_core.models.contracts.subcontracts.model_data_grouping",
        "ModelDataGrouping",
    ),
    "ModelDbOwnershipSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract",
        "ModelDbOwnershipSubcontract",
    ),
    "ModelDbTableDeclaration": (
        "omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract",
        "ModelDbTableDeclaration",
    ),
    "ModelDependencyHealth": (
        "omnibase_core.models.contracts.subcontracts.model_dependency_health",
        "ModelDependencyHealth",
    ),
    "ModelDiscoverySubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_discovery_subcontract",
        "ModelDiscoverySubcontract",
    ),
    "ModelEffectCircuitBreaker": (
        "omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker",
        "ModelEffectCircuitBreaker",
    ),
    "ModelEffectContractMetadata": (
        "omnibase_core.models.contracts.subcontracts.model_effect_contract_metadata",
        "ModelEffectContractMetadata",
    ),
    "ModelEffectInputSchema": (
        "omnibase_core.models.contracts.subcontracts.model_effect_input_schema",
        "ModelEffectInputSchema",
    ),
    "EffectIOConfig": (
        "omnibase_core.models.contracts.subcontracts.model_effect_io_configs",
        "EffectIOConfig",
    ),
    "ModelDbIOConfig": (
        "omnibase_core.models.contracts.subcontracts.model_effect_io_configs",
        "ModelDbIOConfig",
    ),
    "ModelFilesystemIOConfig": (
        "omnibase_core.models.contracts.subcontracts.model_effect_io_configs",
        "ModelFilesystemIOConfig",
    ),
    "ModelHttpIOConfig": (
        "omnibase_core.models.contracts.subcontracts.model_effect_io_configs",
        "ModelHttpIOConfig",
    ),
    "ModelKafkaIOConfig": (
        "omnibase_core.models.contracts.subcontracts.model_effect_io_configs",
        "ModelKafkaIOConfig",
    ),
    "ModelEffectObservability": (
        "omnibase_core.models.contracts.subcontracts.model_effect_observability",
        "ModelEffectObservability",
    ),
    "ModelEffectOperation": (
        "omnibase_core.models.contracts.subcontracts.model_effect_operation",
        "ModelEffectOperation",
    ),
    "ModelEffectOperationResult": (
        "omnibase_core.models.contracts.subcontracts.model_effect_operation_result",
        "ModelEffectOperationResult",
    ),
    "ResolvedIOContext": (
        "omnibase_core.models.contracts.subcontracts.model_effect_resolved_context",
        "ResolvedIOContext",
    ),
    "ModelEffectResponseHandling": (
        "omnibase_core.models.contracts.subcontracts.model_effect_response_handling",
        "ModelEffectResponseHandling",
    ),
    "ModelEffectRetryPolicy": (
        "omnibase_core.models.contracts.subcontracts.model_effect_retry_policy",
        "ModelEffectRetryPolicy",
    ),
    "ModelEffectSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_effect_subcontract",
        "ModelEffectSubcontract",
    ),
    "ModelEffectTransactionConfig": (
        "omnibase_core.models.contracts.subcontracts.model_effect_transaction_config",
        "ModelEffectTransactionConfig",
    ),
    "ModelEnvelopeTemplate": (
        "omnibase_core.models.contracts.subcontracts.model_envelope_template",
        "ModelEnvelopeTemplate",
    ),
    "ModelEventBusSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract",
        "ModelEventBusSubcontract",
    ),
    "ModelEventDefinition": (
        "omnibase_core.models.contracts.subcontracts.model_event_definition",
        "ModelEventDefinition",
    ),
    "ModelEventHandlingSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_event_handling_subcontract",
        "ModelEventHandlingSubcontract",
    ),
    "ModelEventPersistence": (
        "omnibase_core.models.contracts.subcontracts.model_event_persistence",
        "ModelEventPersistence",
    ),
    "ModelEventRouting": (
        "omnibase_core.models.contracts.subcontracts.model_event_routing",
        "ModelEventRouting",
    ),
    "ModelEventTransformation": (
        "omnibase_core.models.contracts.subcontracts.model_event_transformation",
        "ModelEventTransformation",
    ),
    "ModelEventTypeSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_event_type_subcontract",
        "ModelEventTypeSubcontract",
    ),
    "ModelExecutionGraph": (
        "omnibase_core.models.contracts.subcontracts.model_execution_graph",
        "ModelExecutionGraph",
    ),
    "ModelFSMStateDefinition": (
        "omnibase_core.models.contracts.subcontracts.model_fsm_state_definition",
        "ModelFSMStateDefinition",
    ),
    "ModelFSMStateTransition": (
        "omnibase_core.models.contracts.subcontracts.model_fsm_state_transition",
        "ModelFSMStateTransition",
    ),
    "ModelFSMSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_fsm_subcontract",
        "ModelFSMSubcontract",
    ),
    "ModelHandlerRoutingEntry": (
        "omnibase_core.models.contracts.subcontracts.model_handler_routing_entry",
        "ModelHandlerRoutingEntry",
    ),
    "ModelHandlerRoutingSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract",
        "ModelHandlerRoutingSubcontract",
    ),
    "ModelHealthCheckSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_health_check_subcontract",
        "ModelHealthCheckSubcontract",
    ),
    "ModelHookActivation": (
        "omnibase_core.models.contracts.subcontracts.model_hook_activation",
        "ModelHookActivation",
    ),
    "ModelIntrospectionSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_introspection_subcontract",
        "ModelIntrospectionSubcontract",
    ),
    "ModelLifecycleSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_lifecycle_subcontract",
        "ModelLifecycleSubcontract",
    ),
    "ModelLoadBalancing": (
        "omnibase_core.models.contracts.subcontracts.model_load_balancing",
        "ModelLoadBalancing",
    ),
    "ModelLoggingSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_logging_subcontract",
        "ModelLoggingSubcontract",
    ),
    "ModelMetricsSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_metrics_subcontract",
        "ModelMetricsSubcontract",
    ),
    "ModelNodeAssignment": (
        "omnibase_core.models.contracts.subcontracts.model_node_assignment",
        "ModelNodeAssignment",
    ),
    "ModelNodeHealthStatus": (
        "omnibase_core.models.contracts.subcontracts.model_node_health_status",
        "ModelNodeHealthStatus",
    ),
    "ModelNodeProgress": (
        "omnibase_core.models.contracts.subcontracts.model_node_progress",
        "ModelNodeProgress",
    ),
    "ModelObservabilitySubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_observability_subcontract",
        "ModelObservabilitySubcontract",
    ),
    "ModelOperationBindings": (
        "omnibase_core.models.contracts.subcontracts.model_operation_bindings",
        "ModelOperationBindings",
    ),
    "ModelOperationMapping": (
        "omnibase_core.models.contracts.subcontracts.model_operation_mapping",
        "ModelOperationMapping",
    ),
    "ModelPackageHookActivations": (
        "omnibase_core.models.contracts.subcontracts.model_package_hook_activations",
        "ModelPackageHookActivations",
    ),
    "ModelProgressStatus": (
        "omnibase_core.models.contracts.subcontracts.model_progress_status",
        "ModelProgressStatus",
    ),
    "ModelProtocolDependency": (
        "omnibase_core.models.contracts.subcontracts.model_protocol_dependency",
        "ModelProtocolDependency",
    ),
    "ModelReplyTopics": (
        "omnibase_core.models.contracts.subcontracts.model_reply_topics",
        "ModelReplyTopics",
    ),
    "ModelRequestResponseConfig": (
        "omnibase_core.models.contracts.subcontracts.model_request_response_config",
        "ModelRequestResponseConfig",
    ),
    "ModelRequestResponseInstance": (
        "omnibase_core.models.contracts.subcontracts.model_request_response_instance",
        "ModelRequestResponseInstance",
    ),
    "ModelRequestTransformation": (
        "omnibase_core.models.contracts.subcontracts.model_request_transformation",
        "ModelRequestTransformation",
    ),
    "ModelResolvedDbContext": (
        "omnibase_core.models.contracts.subcontracts.model_resolved_db_context",
        "ModelResolvedDbContext",
    ),
    "ModelResolvedFilesystemContext": (
        "omnibase_core.models.contracts.subcontracts.model_resolved_filesystem_context",
        "ModelResolvedFilesystemContext",
    ),
    "ModelResolvedHttpContext": (
        "omnibase_core.models.contracts.subcontracts.model_resolved_http_context",
        "ModelResolvedHttpContext",
    ),
    "ModelResolvedKafkaContext": (
        "omnibase_core.models.contracts.subcontracts.model_resolved_kafka_context",
        "ModelResolvedKafkaContext",
    ),
    "ModelResponseMapping": (
        "omnibase_core.models.contracts.subcontracts.model_response_mapping",
        "ModelResponseMapping",
    ),
    "ModelRetrievalSource": (
        "omnibase_core.models.contracts.subcontracts.model_retrieval_source",
        "ModelRetrievalSource",
    ),
    "ModelRetrySubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_retry_subcontract",
        "ModelRetrySubcontract",
    ),
    "ModelReturnSchema": (
        "omnibase_core.models.contracts.subcontracts.model_return_schema",
        "ModelReturnSchema",
    ),
    "ModelRouteDefinition": (
        "omnibase_core.models.contracts.subcontracts.model_route_definition",
        "ModelRouteDefinition",
    ),
    "ModelRoutingMetrics": (
        "omnibase_core.models.contracts.subcontracts.model_routing_metrics",
        "ModelRoutingMetrics",
    ),
    "ModelRoutingSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_routing_subcontract",
        "ModelRoutingSubcontract",
    ),
    "ModelRuntimeLaneScope": (
        "omnibase_core.models.contracts.subcontracts.model_runtime_lane_scope",
        "ModelRuntimeLaneScope",
    ),
    "ModelSecuritySubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_security_subcontract",
        "ModelSecuritySubcontract",
    ),
    "ModelSerializationSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_serialization_subcontract",
        "ModelSerializationSubcontract",
    ),
    "ModelStateManagementSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_state_management_subcontract",
        "ModelStateManagementSubcontract",
    ),
    "ModelStatePersistence": (
        "omnibase_core.models.contracts.subcontracts.model_state_persistence",
        "ModelStatePersistence",
    ),
    "ModelStateSynchronization": (
        "omnibase_core.models.contracts.subcontracts.model_state_synchronization",
        "ModelStateSynchronization",
    ),
    "ModelStateValidation": (
        "omnibase_core.models.contracts.subcontracts.model_state_validation",
        "ModelStateValidation",
    ),
    "ModelStateVersioning": (
        "omnibase_core.models.contracts.subcontracts.model_state_versioning",
        "ModelStateVersioning",
    ),
    "ModelStatisticalComputation": (
        "omnibase_core.models.contracts.subcontracts.model_statistical_computation",
        "ModelStatisticalComputation",
    ),
    "ModelSynchronizationPoint": (
        "omnibase_core.models.contracts.subcontracts.model_synchronization_point",
        "ModelSynchronizationPoint",
    ),
    "ModelToolExecutionSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_tool_execution_subcontract",
        "ModelToolExecutionSubcontract",
    ),
    "ModelTopicMeta": (
        "omnibase_core.models.contracts.subcontracts.model_topic_meta",
        "ModelTopicMeta",
    ),
    "ModelTopicProvisioningConfig": (
        "omnibase_core.models.contracts.subcontracts.model_topic_provisioning_config",
        "ModelTopicProvisioningConfig",
    ),
    "ModelValidationSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_validation_subcontract",
        "ModelValidationSubcontract",
    ),
    "ModelValidatorRule": (
        "omnibase_core.models.contracts.subcontracts.model_validator_rule",
        "ModelValidatorRule",
    ),
    "ModelValidatorSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_validator_subcontract",
        "ModelValidatorSubcontract",
    ),
    "ModelWindowingStrategy": (
        "omnibase_core.models.contracts.subcontracts.model_windowing_strategy",
        "ModelWindowingStrategy",
    ),
    "ModelWorkflowCoordinationSubcontract": (
        "omnibase_core.models.contracts.subcontracts.model_workflow_coordination_subcontract",
        "ModelWorkflowCoordinationSubcontract",
    ),
    "ModelWorkflowDefinition": (
        "omnibase_core.models.contracts.subcontracts.model_workflow_definition",
        "ModelWorkflowDefinition",
    ),
    "ModelWorkflowDefinitionMetadata": (
        "omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata",
        "ModelWorkflowDefinitionMetadata",
    ),
    "ModelWorkflowInstance": (
        "omnibase_core.models.contracts.subcontracts.model_workflow_instance",
        "ModelWorkflowInstance",
    ),
    "ModelWorkflowNode": (
        "omnibase_core.models.contracts.subcontracts.model_workflow_node",
        "ModelWorkflowNode",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
