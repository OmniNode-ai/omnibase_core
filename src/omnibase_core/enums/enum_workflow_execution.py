"""
Workflow Execution Enums.

Enums for workflow orchestration including execution modes,
action types, and branch conditions.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.

Note: EnumWorkflowState has been consolidated into EnumWorkflowStatus
in enum_workflow_status.py per OMN-1310.
"""

from enum import Enum, unique


@unique
class EnumExecutionMode(Enum):
    """Execution modes for workflow steps."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    BATCH = "batch"
    STREAMING = "streaming"


@unique
class EnumActionType(Enum):
    """Types of Actions for orchestrated execution."""

    COMPUTE = "compute"
    EFFECT = "effect"
    REDUCE = "reduce"
    ORCHESTRATE = "orchestrate"
    CUSTOM = "custom"


@unique
class EnumBranchCondition(Enum):
    """Conditional branching types."""

    IF_TRUE = "if_true"
    IF_FALSE = "if_false"
    IF_ERROR = "if_error"
    IF_SUCCESS = "if_success"
    IF_TIMEOUT = "if_timeout"
    CUSTOM = "custom"
