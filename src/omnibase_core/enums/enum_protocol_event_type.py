"""
Event type enumeration for ONEX protocol-based event publishing.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumProtocolEventType(StrValueHelper, str, Enum):
    """Standard event types for protocol-based event publishing."""

    # EnumLifecycle events
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"

    # State events
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    # Workflow events
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_STEP_COMPLETED = "WORKFLOW_STEP_COMPLETED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"

    # Intelligence events
    INTELLIGENCE_CAPTURED = "INTELLIGENCE_CAPTURED"
    INTELLIGENCE_ANALYZED = "INTELLIGENCE_ANALYZED"
    INTELLIGENCE_STORED = "INTELLIGENCE_STORED"

    # Validation events
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"

    # Generation events
    GENERATION_REQUESTED = "GENERATION_REQUESTED"
    GENERATION_STARTED = "GENERATION_STARTED"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"
    GENERATION_FAILED = "GENERATION_FAILED"

    # System events
    HEALTH_CHECK = "HEALTH_CHECK"
    METRICS_REPORTED = "METRICS_REPORTED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    WARNING_RAISED = "WARNING_RAISED"

    # Custom events
    CUSTOM = "CUSTOM"  # For domain-specific events


__all__ = ["EnumProtocolEventType"]
