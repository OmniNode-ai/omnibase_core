"""
Communication models package.

This package contains models for agent communication, progress tracking,
and result reporting in the ONEX system.
"""

from .model_agent_event import AgentEventSeverity, AgentEventType, ModelAgentEvent
from .model_progress_update import (
    ModelProgressUpdate,
    ModelStepProgress,
    ProgressStatus,
)
from .model_work_result import (
    ModelFileChange,
    ModelValidationResult,
    ModelWorkResult,
    WorkResultStatus,
)

__all__ = [
    "AgentEventSeverity",
    "AgentEventType",
    "ModelAgentEvent",
    "ModelFileChange",
    "ModelProgressUpdate",
    "ModelStepProgress",
    "ModelValidationResult",
    "ModelWorkResult",
    "ProgressStatus",
    "WorkResultStatus",
]
