"""
Workflow Coordination Enums.

Comprehensive enum definitions for workflow coordination functionality including
workflow status, assignment status, execution patterns, and failure recovery
strategies for ORCHESTRATOR nodes.
"""

from enum import Enum


class EnumWorkflowStatus(str, Enum):
    """Workflow execution status."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EnumAssignmentStatus(str, Enum):
    """Node assignment status."""

    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EnumExecutionPattern(str, Enum):
    """Workflow execution patterns."""

    SEQUENTIAL = "sequential"
    PARALLEL_COMPUTE = "parallel_compute"
    PIPELINE = "pipeline"
    SCATTER_GATHER = "scatter_gather"


class EnumFailureRecoveryStrategy(str, Enum):
    """Failure recovery strategies."""

    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"  # RESERVED - v2.0
    COMPENSATE = "COMPENSATE"  # RESERVED - v2.0
    ABORT = "ABORT"
