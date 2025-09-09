"""Reducer Pattern Engine - Multi-workflow execution with instance isolation.

Phase 1: Core Demo Implementation
- WorkflowRouter for hash-based routing
- Single subreducer for document regeneration workflows
- ONEX four-node architecture compliance
"""

from .v1_0_0.engine import ReducerPatternEngine
from .v1_0_0.models import ModelRoutingDecision as RoutingDecision
from .v1_0_0.models import ModelSubreducerResult as SubreducerResult
from .v1_0_0.models import ModelWorkflowRequest as WorkflowRequest
from .v1_0_0.models import ModelWorkflowResponse as WorkflowResponse
from .v1_0_0.router import WorkflowRouter

__all__ = [
    "ReducerPatternEngine",
    "RoutingDecision",
    "SubreducerResult",
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowRouter",
]
