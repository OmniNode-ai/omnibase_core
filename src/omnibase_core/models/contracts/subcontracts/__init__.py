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
from .model_aggregation_subcontract import ModelAggregationSubcontract
from .model_caching_subcontract import (
    ModelCacheDistribution,
    ModelCacheInvalidation,
    ModelCacheKeyStrategy,
    ModelCachePerformance,
    ModelCachingSubcontract,
)
from .model_configuration_subcontract import ModelConfigurationSubcontract
from .model_event_type_subcontract import ModelEventTypeSubcontract
from .model_fsm_subcontract import ModelFSMSubcontract
from .model_routing_subcontract import (
    ModelCircuitBreaker,
    ModelLoadBalancing,
    ModelRequestTransformation,
    ModelRouteDefinition,
    ModelRoutingMetrics,
    ModelRoutingSubcontract,
)
from .model_state_management_subcontract import ModelStateManagementSubcontract
from .model_workflow_coordination_subcontract import (
    ModelWorkflowCoordinationSubcontract,
)

__all__ = [
    # Aggregation subcontracts
    "ModelAggregationSubcontract",
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
    # FSM subcontracts
    "ModelFSMSubcontract",
    # Routing subcontracts
    "ModelCircuitBreaker",
    "ModelLoadBalancing",
    "ModelRequestTransformation",
    "ModelRouteDefinition",
    "ModelRoutingMetrics",
    "ModelRoutingSubcontract",
    # State management subcontracts
    "ModelStateManagementSubcontract",
    # Workflow coordination subcontracts
    "ModelWorkflowCoordinationSubcontract",
]
