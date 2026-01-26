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

# Re-export constant from canonical location
from omnibase_core.constants import IDEMPOTENCY_DEFAULTS
from omnibase_core.models.core.model_health_check_result import ModelHealthCheckResult
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
from .model_coordination_result import ModelCoordinationResult
from .model_coordination_rules import ModelCoordinationRules
from .model_data_grouping import ModelDataGrouping
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
from .model_progress_status import ModelProgressStatus
from .model_request_transformation import ModelRequestTransformation
from .model_resolved_db_context import ModelResolvedDbContext
from .model_resolved_filesystem_context import ModelResolvedFilesystemContext
from .model_resolved_http_context import ModelResolvedHttpContext
from .model_resolved_kafka_context import ModelResolvedKafkaContext
from .model_response_mapping import ModelResponseMapping
from .model_retry_subcontract import ModelRetrySubcontract
from .model_route_definition import ModelRouteDefinition
from .model_routing_metrics import ModelRoutingMetrics
from .model_routing_subcontract import ModelRoutingSubcontract
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
    # Circuit breaker subcontracts
    "ModelCircuitBreakerSubcontract",
    # Compute subcontracts and components
    "ModelComputePipelineStep",
    "ModelComputeSubcontract",
    # Configuration subcontracts and components
    "ModelConfigurationSubcontract",
    "ModelConfigurationSource",
    "ModelConfigurationValidation",
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
    "ModelTopicMeta",
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
