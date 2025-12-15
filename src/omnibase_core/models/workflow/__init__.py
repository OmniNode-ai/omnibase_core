"""
Workflow Models

Consolidated workflow models for ONEX framework.
Organized into API (external interface) and Execution (internal orchestration).
"""

# API Models - External interface for workflow operations
from .api import (
    ModelWorkflowExecutionArgs,
    ModelWorkflowListResult,
    ModelWorkflowOutputs,
    ModelWorkflowStatusResult,
    ModelWorkflowStopArgs,
)

# Execution Models - Internal workflow execution and orchestration
from .execution import (
    WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
    ModelDependencyGraph,
    ModelWorkflowExecutionResult,
    ModelWorkflowInputState,
    ModelWorkflowStateSnapshot,
    ModelWorkflowStepExecution,
)

__all__ = [
    # API Models
    "ModelWorkflowExecutionArgs",
    "ModelWorkflowListResult",
    "ModelWorkflowOutputs",
    "ModelWorkflowStatusResult",
    "ModelWorkflowStopArgs",
    # Execution Models
    "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION",
    "ModelDependencyGraph",
    "ModelWorkflowExecutionResult",
    "ModelWorkflowInputState",
    "ModelWorkflowStateSnapshot",
    "ModelWorkflowStepExecution",
]
