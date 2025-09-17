"""Reducer Pattern Engine v1.0.0 - Phase 3 ONEX Protocol Compliance."""

# Core Engine Components
# Contract Model
from .contracts.model_contract_reducer_pattern_engine import (
    ModelContractReducerPatternEngine,
)
from .engine import ReducerPatternEngine
from .metrics import ReducerMetricsCollector

# ONEX-Compliant Models
from .models import (
    BaseSubreducer,
    ModelReducerPatternEngineInput,
    ModelReducerPatternEngineOutput,
    ModelRoutingDecision,
    ModelSubreducerResult,
    ModelWorkflowMetrics,
    ModelWorkflowRequest,
    ModelWorkflowResponse,
    WorkflowStatus,
    WorkflowType,
)

# ONEX Protocol Compliance - Phase 3
from .node_reducer_pattern_engine import NodeReducerPatternEngine

# Protocol Definitions
from .protocols import (
    BaseReducerPatternEngine,
    ProtocolReducerPatternEngine,
)
from .registry import ReducerSubreducerRegistry
from .router import WorkflowRouter

# Convenience aliases
RoutingDecision = ModelRoutingDecision
SubreducerResult = ModelSubreducerResult
WorkflowMetrics = ModelWorkflowMetrics
WorkflowRequest = ModelWorkflowRequest
WorkflowResponse = ModelWorkflowResponse

# ONEX Input/Output aliases
EngineInput = ModelReducerPatternEngineInput
EngineOutput = ModelReducerPatternEngineOutput

__all__ = [
    # Phase 3 Main Components
    "NodeReducerPatternEngine",
    "ProtocolReducerPatternEngine",
    "BaseReducerPatternEngine",
    "ModelContractReducerPatternEngine",
    # ONEX Models
    "ModelReducerPatternEngineInput",
    "ModelReducerPatternEngineOutput",
    "EngineInput",
    "EngineOutput",
    # Core Engine Components
    "ReducerPatternEngine",
    "WorkflowRouter",
    "ReducerSubreducerRegistry",
    "ReducerMetricsCollector",
    # Workflow Models
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowStatus",
    "WorkflowType",
    "WorkflowMetrics",
    # Supporting Models
    "RoutingDecision",
    "SubreducerResult",
    "BaseSubreducer",
    # Model Classes (explicit)
    "ModelRoutingDecision",
    "ModelSubreducerResult",
    "ModelWorkflowMetrics",
    "ModelWorkflowRequest",
    "ModelWorkflowResponse",
]
