#!/usr/bin/env python3
"""
Core ONEX Subcontract Models.

Provides dedicated Pydantic models for all ONEX subcontract patterns:
- FSM (Finite State Machine) subcontracts
- Event Type subcontracts
- Caching subcontracts
- Routing subcontracts
- State Management subcontracts
- Aggregation subcontracts

These models are composed into node contracts via Union types and optional fields,
providing clean separation between node logic and subcontract functionality.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

# Import workflow coordination subcontract from models directory
from omnibase_core.models.subcontracts.model_workflow_coordination_subcontract import (
    ModelWorkflowCoordinationSubcontract,
)

from .model_aggregation_subcontract import ModelAggregationSubcontract
from .model_caching_subcontract import ModelCachingSubcontract
from .model_event_type_subcontract import ModelEventTypeSubcontract
from .model_fsm_subcontract import ModelFSMSubcontract
from .model_routing_subcontract import ModelRoutingSubcontract
from .model_state_management_subcontract import ModelStateManagementSubcontract

__all__ = [
    "ModelAggregationSubcontract",
    "ModelCachingSubcontract",
    "ModelEventTypeSubcontract",
    "ModelFSMSubcontract",
    "ModelRoutingSubcontract",
    "ModelStateManagementSubcontract",
    "ModelWorkflowCoordinationSubcontract",
]
