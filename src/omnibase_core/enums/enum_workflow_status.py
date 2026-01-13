"""
Workflow status enumeration.

Enumeration of possible workflow execution status values for ONEX workflows.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumWorkflowStatus(StrValueHelper, str, Enum):
    """Workflow execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SIMULATED = "simulated"
