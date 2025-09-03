"""Reducer Pattern Engine - Multi-workflow execution with instance isolation.

Phase 1: Core Demo Implementation
- WorkflowRouter for hash-based routing
- Single subreducer for document regeneration workflows
- ONEX four-node architecture compliance
"""

from .v1_0_0.contracts import (
    RoutingDecision,
    SubreducerResult,
    WorkflowRequest,
    WorkflowResponse,
)
from .v1_0_0.engine import ReducerPatternEngine
from .v1_0_0.router import WorkflowRouter

__all__ = [
    "ReducerPatternEngine",
    "WorkflowRouter",
    "WorkflowRequest",
    "WorkflowResponse",
    "RoutingDecision",
    "SubreducerResult",
]
