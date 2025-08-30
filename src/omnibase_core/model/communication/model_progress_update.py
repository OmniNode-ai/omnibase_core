"""
Model for work progress updates from Claude Code agents.

This model represents progress updates sent by agents during work execution
to provide real-time status information to the ONEX system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProgressStatus(str, Enum):
    """Progress status enumeration."""

    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETING = "completing"
    PAUSED = "paused"
    BLOCKED = "blocked"


class ModelStepProgress(BaseModel):
    """Individual step progress within a task."""

    step_id: str = Field(description="Unique identifier for this step")
    step_name: str = Field(description="Human-readable step name")
    status: ProgressStatus = Field(description="Current status of this step")
    progress_percent: float = Field(
        description="Progress percentage (0-100) for this step"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Step start timestamp"
    )
    estimated_completion: Optional[datetime] = Field(
        default=None, description="Estimated completion time for this step"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if step failed"
    )


class ModelProgressUpdate(BaseModel):
    """Progress update from Claude Code agent."""

    update_id: str = Field(description="Unique identifier for this progress update")
    agent_id: str = Field(description="ID of the agent sending this update")
    task_id: str = Field(description="ID of the task being executed")
    ticket_id: Optional[str] = Field(
        default=None, description="ID of the work ticket being processed"
    )
    overall_progress: float = Field(description="Overall progress percentage (0-100)")
    status: ProgressStatus = Field(description="Current overall status")
    current_operation: str = Field(description="Description of current operation")
    steps: List[ModelStepProgress] = Field(
        default_factory=list, description="Progress of individual steps"
    )
    files_modified: List[str] = Field(
        default_factory=list, description="List of files modified so far"
    )
    files_created: List[str] = Field(
        default_factory=list, description="List of files created so far"
    )
    estimated_completion: Optional[datetime] = Field(
        default=None, description="Estimated completion time for entire task"
    )
    elapsed_time_seconds: int = Field(
        description="Elapsed time since task start in seconds"
    )
    remaining_time_seconds: Optional[int] = Field(
        default=None, description="Estimated remaining time in seconds"
    )
    resource_usage: Optional[Dict[str, float]] = Field(
        default=None, description="Current resource usage metrics"
    )
    validation_results: Optional[Dict[str, bool]] = Field(
        default=None, description="Validation results so far"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Any warnings encountered"
    )
    blockers: List[str] = Field(
        default_factory=list, description="Current blocking issues"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Update timestamp"
    )
    session_id: Optional[str] = Field(
        default=None, description="Agent session identifier"
    )
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracking related events"
    )

    @property
    def is_blocked(self) -> bool:
        """Check if progress is currently blocked."""
        return self.status == ProgressStatus.BLOCKED or len(self.blockers) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def completion_percentage(self) -> int:
        """Get completion percentage as integer."""
        return int(min(100, max(0, self.overall_progress)))

    @property
    def current_step(self) -> Optional[ModelStepProgress]:
        """Get the currently active step."""
        for step in self.steps:
            if step.status == ProgressStatus.IN_PROGRESS:
                return step
        return None

    @property
    def completed_steps(self) -> List[ModelStepProgress]:
        """Get list of completed steps."""
        return [step for step in self.steps if step.progress_percent >= 100]
