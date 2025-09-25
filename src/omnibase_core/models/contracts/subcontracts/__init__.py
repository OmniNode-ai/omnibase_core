#!/usr/bin/env python3
"""
ONEX Subcontract Models - Contracts Module.

Provides dedicated Pydantic models for all ONEX subcontract patterns:
- Aggregation: Data aggregation patterns and policies
- Caching: Cache strategies, invalidation, and performance tuning
- Configuration: Configuration management and validation
- Event Type: Event type definitions and routing
- FSM (Finite State Machine): State machine behavior and transitions
- Routing: Message routing and load balancing strategies
- State Management: State persistence and synchronization
- Workflow Coordination: Multi-step workflow orchestration

These models are composed into node contracts via Union types and optional fields,
providing clean separation between node logic and subcontract functionality.

ONEX Compliance: Strong typing with zero tolerance for Any types.
"""

# Subcontract model imports (alphabetical order)
from .model_aggregation_function import ModelAggregationFunction
from .model_aggregation_performance import ModelAggregationPerformance
from .model_aggregation_subcontract import ModelAggregationSubcontract
from .model_caching_subcontract import (
    ModelCacheDistribution,
    ModelCacheInvalidation,
    ModelCacheKeyStrategy,
    ModelCachePerformance,
    ModelCachingSubcontract,
)
from .model_circuit_breaker import ModelCircuitBreaker
from .model_configuration_subcontract import ModelConfigurationSubcontract
from .model_data_grouping import ModelDataGrouping
from .model_event_type_subcontract import ModelEventTypeSubcontract
from .model_fsm_operation import ModelFSMOperation
from .model_fsm_state_definition import ModelFSMStateDefinition
from .model_fsm_state_transition import ModelFSMStateTransition
from .model_fsm_subcontract import ModelFSMSubcontract
from .model_fsm_transition_action import ModelFSMTransitionAction
from .model_fsm_transition_condition import ModelFSMTransitionCondition
from .model_load_balancing import ModelLoadBalancing
from .model_request_transformation import ModelRequestTransformation
from .model_route_definition import ModelRouteDefinition
from .model_routing_metrics import ModelRoutingMetrics
from .model_routing_subcontract import ModelRoutingSubcontract
from .model_state_management_subcontract import ModelStateManagementSubcontract
from .model_state_persistence import ModelStatePersistence
from .model_state_synchronization import ModelStateSynchronization
from .model_state_validation import ModelStateValidation
from .model_state_versioning import ModelStateVersioning
from .model_statistical_computation import ModelStatisticalComputation
from .model_windowing_strategy import ModelWindowingStrategy
from .model_workflow_coordination_subcontract import (
    ModelWorkflowCoordinationSubcontract,
)

__all__ = [
    # Aggregation subcontracts and components
    "ModelAggregationSubcontract",
    "ModelAggregationFunction",
    "ModelAggregationPerformance",
    "ModelDataGrouping",
    "ModelStatisticalComputation",
    "ModelWindowingStrategy",
    # Caching subcontracts
    "ModelCacheDistribution",
    "ModelCacheInvalidation",
    "ModelCacheKeyStrategy",
    "ModelCachePerformance",
    "ModelCachingSubcontract",
    # Configuration subcontracts
    "ModelConfigurationSubcontract",
    # Event type subcontracts
    "ModelEventTypeSubcontract",
    # FSM subcontracts and components
    "ModelFSMSubcontract",
    "ModelFSMOperation",
    "ModelFSMStateDefinition",
    "ModelFSMStateTransition",
    "ModelFSMTransitionAction",
    "ModelFSMTransitionCondition",
    # Routing subcontracts and components
    "ModelRoutingSubcontract",
    "ModelCircuitBreaker",
    "ModelLoadBalancing",
    "ModelRequestTransformation",
    "ModelRouteDefinition",
    "ModelRoutingMetrics",
    # State management subcontracts and components
    "ModelStateManagementSubcontract",
    "ModelStatePersistence",
    "ModelStateSynchronization",
    "ModelStateValidation",
    "ModelStateVersioning",
    # Workflow coordination subcontracts
    "ModelWorkflowCoordinationSubcontract",
]
