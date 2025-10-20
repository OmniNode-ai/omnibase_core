"""
Workflow status enumeration.

Enumeration of possible workflow execution status values for ONEX workflows.
"""

from enum import Enum


class EnumWorkflowStatus(str, Enum):
    """Workflow execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SIMULATED = "simulated"
