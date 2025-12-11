"""
Enums for NodeOrchestrator workflow coordination.

Extracted from archived NodeOrchestrator for ONEX compliance.
"""

from enum import Enum


class EnumWorkflowState(Enum):
    """Workflow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # RESERVED - v1.1
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnumExecutionMode(Enum):
    """Execution modes for workflow steps."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"  # RESERVED - v1.1
    BATCH = "batch"
    STREAMING = "streaming"  # RESERVED - v1.2


class EnumActionType(Enum):
    """Types of Actions for orchestrated execution."""

    COMPUTE = "compute"
    EFFECT = "effect"
    REDUCE = "reduce"
    ORCHESTRATE = "orchestrate"
    CUSTOM = "custom"


class EnumBranchCondition(Enum):
    """Conditional branching types."""

    IF_TRUE = "if_true"
    IF_FALSE = "if_false"
    IF_ERROR = "if_error"
    IF_SUCCESS = "if_success"
    IF_TIMEOUT = "if_timeout"
    CUSTOM = "custom"
