"""
Workflow Coordination Enums.

Comprehensive enum definitions for workflow coordination functionality including
assignment status, execution patterns, and failure recovery strategies
for ORCHESTRATOR nodes.

Note: EnumWorkflowStatus has been consolidated into the canonical version
in enum_workflow_status.py per OMN-1310.
"""

from enum import Enum, unique


@unique
class EnumAssignmentStatus(str, Enum):
    """Node assignment status."""

    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@unique
class EnumExecutionPattern(str, Enum):
    """Workflow execution patterns."""

    SEQUENTIAL = "sequential"
    PARALLEL_COMPUTE = "parallel_compute"
    PIPELINE = "pipeline"
    SCATTER_GATHER = "scatter_gather"


@unique
class EnumFailureRecoveryStrategy(str, Enum):
    """Failure recovery strategies."""

    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"  # RESERVED - v2.0
    COMPENSATE = "COMPENSATE"  # RESERVED - v2.0
    ABORT = "ABORT"
