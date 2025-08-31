"""
Model for work assignments between tickets and agents.

This model represents the assignment relationship and tracking data
for work tickets assigned to Claude Code agents.
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.model.work.model_work_ticket import WorkTicketPriority


class AssignmentStatus(str, Enum):
    """Assignment status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REASSIGNED = "reassigned"


class AssignmentReason(str, Enum):
    """Reason for assignment enumeration."""

    AUTO_ASSIGNED = "auto_assigned"
    MANUALLY_ASSIGNED = "manually_assigned"
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCING = "load_balancing"
    DEPENDENCY_RESOLVED = "dependency_resolved"
    REASSIGNMENT = "reassignment"
    FAILOVER = "failover"


class ModelWorkAssignmentMetrics(BaseModel):
    """Metrics tracking for work assignment."""

    estimated_duration_hours: float | None = Field(
        default=None,
        description="Estimated time to complete the work in hours",
    )
    actual_duration_hours: float | None = Field(
        default=None,
        description="Actual time taken to complete the work",
    )
    complexity_score: float | None = Field(
        default=None,
        description="Complexity score (1-10 scale)",
    )
    effort_estimate: float | None = Field(
        default=None,
        description="Effort estimate in story points or hours",
    )
    files_modified_count: int = Field(
        default=0,
        description="Number of files modified during assignment",
    )
    lines_added: int = Field(default=0, description="Number of lines added")
    lines_removed: int = Field(default=0, description="Number of lines removed")
    tests_added: int = Field(default=0, description="Number of tests added")
    bugs_fixed: int = Field(default=0, description="Number of bugs fixed")
    features_implemented: int = Field(
        default=0,
        description="Number of features implemented",
    )


class ModelWorkAssignmentHistory(BaseModel):
    """History entry for assignment changes."""

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of the history entry",
    )
    action: str = Field(
        description="Action taken (assigned, started, paused, resumed, completed, etc.)",
    )
    previous_status: AssignmentStatus | None = Field(
        default=None,
        description="Previous assignment status",
    )
    new_status: AssignmentStatus = Field(description="New assignment status")
    actor: str = Field(description="Who or what triggered this change")
    reason: str | None = Field(default=None, description="Reason for the change")
    additional_data: dict[str, str] | None = Field(
        default=None,
        description="Additional data about the change",
    )


class ModelWorkAssignment(BaseModel):
    """Work assignment between ticket and agent."""

    assignment_id: str = Field(description="Unique identifier for this assignment")
    ticket_id: str = Field(description="ID of the work ticket")
    agent_id: str = Field(description="ID of the assigned agent")
    status: AssignmentStatus = Field(
        default=AssignmentStatus.PENDING,
        description="Current status of the assignment",
    )
    priority: WorkTicketPriority = Field(
        description="Priority level of the assigned work",
    )
    assignment_reason: AssignmentReason = Field(
        default=AssignmentReason.AUTO_ASSIGNED,
        description="Reason for this assignment",
    )
    assigned_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when assignment was made",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when work actually started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when work was completed",
    )
    deadline: datetime | None = Field(
        default=None,
        description="Deadline for completion",
    )
    assigned_by: str = Field(description="Who or what made the assignment")
    reservation_expires_at: datetime | None = Field(
        default=None,
        description="When the assignment reservation expires",
    )
    progress_percent: float = Field(
        default=0.0,
        description="Current progress percentage (0-100)",
    )
    current_phase: str | None = Field(
        default=None,
        description="Current phase of work (analysis, implementation, testing, etc.)",
    )
    estimated_completion: datetime | None = Field(
        default=None,
        description="Estimated completion time",
    )
    checkpoint_data: dict[str, str] | None = Field(
        default=None,
        description="Checkpoint data for work resumption",
    )
    metrics: ModelWorkAssignmentMetrics = Field(
        default_factory=ModelWorkAssignmentMetrics,
        description="Assignment performance metrics",
    )
    history: list[ModelWorkAssignmentHistory] = Field(
        default_factory=list,
        description="History of assignment changes",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of ticket IDs this assignment depends on",
    )
    blocked_by: list[str] = Field(
        default_factory=list,
        description="List of ticket IDs blocking this assignment",
    )
    blocks: list[str] = Field(
        default_factory=list,
        description="List of ticket IDs this assignment blocks",
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="Required capabilities for this assignment",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    notes: list[str] = Field(
        default_factory=list,
        description="Additional notes about the assignment",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if assignment failed",
    )
    retry_count: int = Field(
        default=0,
        description="Number of times this assignment has been retried",
    )
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    last_heartbeat: datetime | None = Field(
        default=None,
        description="Last heartbeat from working agent",
    )
    working_directory: str | None = Field(
        default=None,
        description="Working directory for this assignment",
    )
    configuration_overrides: dict[str, str] | None = Field(
        default=None,
        description="Configuration overrides for this assignment",
    )

    @property
    def is_active(self) -> bool:
        """Check if assignment is currently active."""
        return self.status == AssignmentStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if assignment is completed."""
        return self.status == AssignmentStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if assignment has failed."""
        return self.status == AssignmentStatus.FAILED

    @property
    def is_overdue(self) -> bool:
        """Check if assignment is overdue."""
        return (
            self.deadline is not None
            and datetime.now() > self.deadline
            and not self.is_completed
        )

    @property
    def is_reserved(self) -> bool:
        """Check if assignment is currently reserved."""
        return (
            self.reservation_expires_at is not None
            and datetime.now() < self.reservation_expires_at
        )

    @property
    def elapsed_time(self) -> timedelta | None:
        """Get elapsed time since work started."""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return end_time - self.started_at
        return None

    @property
    def total_assignment_time(self) -> timedelta:
        """Get total time since assignment was made."""
        end_time = self.completed_at or datetime.now()
        return end_time - self.assigned_at

    @property
    def time_to_start(self) -> timedelta | None:
        """Get time between assignment and actual start."""
        if self.started_at:
            return self.started_at - self.assigned_at
        return None

    @property
    def completion_percentage(self) -> int:
        """Get completion percentage as integer."""
        return int(min(100, max(0, self.progress_percent)))

    @property
    def estimated_remaining_time(self) -> timedelta | None:
        """Estimate remaining time based on progress and elapsed time."""
        if self.elapsed_time and self.progress_percent > 0:
            total_estimated = self.elapsed_time.total_seconds() / (
                self.progress_percent / 100
            )
            remaining_seconds = total_estimated - self.elapsed_time.total_seconds()
            return timedelta(seconds=max(0, remaining_seconds))
        return None

    @property
    def is_stale(self) -> bool:
        """Check if assignment appears stale (no recent heartbeat)."""
        if not self.last_heartbeat:
            return True
        return datetime.now() - self.last_heartbeat > timedelta(minutes=10)

    @property
    def can_retry(self) -> bool:
        """Check if assignment can be retried."""
        return self.retry_count < self.max_retries

    @property
    def is_blocked(self) -> bool:
        """Check if assignment is blocked by dependencies."""
        return len(self.blocked_by) > 0

    def add_history_entry(
        self,
        action: str,
        new_status: AssignmentStatus,
        actor: str,
        reason: str | None = None,
    ) -> None:
        """Add an entry to the assignment history."""
        entry = ModelWorkAssignmentHistory(
            action=action,
            previous_status=self.status,
            new_status=new_status,
            actor=actor,
            reason=reason,
        )
        self.history.append(entry)
        self.status = new_status

    def start_work(self) -> None:
        """Mark assignment as started."""
        self.started_at = datetime.now()
        self.add_history_entry("started", AssignmentStatus.ACTIVE, "system")

    def pause_work(self, reason: str | None = None) -> None:
        """Pause the work assignment."""
        self.add_history_entry("paused", AssignmentStatus.PAUSED, "system", reason)

    def resume_work(self) -> None:
        """Resume the work assignment."""
        self.add_history_entry("resumed", AssignmentStatus.ACTIVE, "system")

    def complete_work(self, success: bool = True) -> None:
        """Mark assignment as completed."""
        self.completed_at = datetime.now()
        self.progress_percent = 100.0

        if success:
            self.add_history_entry("completed", AssignmentStatus.COMPLETED, "system")
        else:
            self.add_history_entry("failed", AssignmentStatus.FAILED, "system")

        # Calculate actual duration
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.metrics.actual_duration_hours = duration.total_seconds() / 3600

    def fail_assignment(self, error_message: str) -> None:
        """Mark assignment as failed."""
        self.error_message = error_message
        self.add_history_entry(
            "failed",
            AssignmentStatus.FAILED,
            "system",
            error_message,
        )

    def reassign(self, new_agent_id: str, reason: str) -> None:
        """Reassign to a different agent."""
        old_agent = self.agent_id
        self.agent_id = new_agent_id
        self.retry_count += 1
        self.add_history_entry(
            "reassigned",
            AssignmentStatus.PENDING,
            "system",
            f"Reassigned from {old_agent} to {new_agent_id}: {reason}",
        )

    def update_progress(self, percent: float, phase: str | None = None) -> None:
        """Update assignment progress."""
        self.progress_percent = max(0.0, min(100.0, percent))
        if phase:
            self.current_phase = phase

        # Update estimated completion if we have a start time
        if self.started_at and self.progress_percent > 0:
            elapsed = datetime.now() - self.started_at
            total_estimated = elapsed.total_seconds() / (self.progress_percent / 100)
            self.estimated_completion = self.started_at + timedelta(
                seconds=total_estimated,
            )

    def add_note(self, note: str) -> None:
        """Add a note to the assignment."""
        timestamp = datetime.now().isoformat()
        self.notes.append(f"[{timestamp}] {note}")

    def heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now()

    def extend_reservation(self, minutes: int) -> None:
        """Extend the reservation time."""
        if self.reservation_expires_at:
            self.reservation_expires_at += timedelta(minutes=minutes)
        else:
            self.reservation_expires_at = datetime.now() + timedelta(minutes=minutes)

    def create_checkpoint(self, data: dict[str, str]) -> None:
        """Create a checkpoint with current state."""
        self.checkpoint_data = {
            **data,
            "checkpoint_time": datetime.now().isoformat(),
            "progress_percent": str(self.progress_percent),
            "current_phase": self.current_phase or "",
        }

    def get_performance_score(self) -> float | None:
        """Calculate performance score based on metrics."""
        if (
            not self.metrics.estimated_duration_hours
            or not self.metrics.actual_duration_hours
        ):
            return None

        # Basic score based on time efficiency
        time_efficiency = (
            self.metrics.estimated_duration_hours / self.metrics.actual_duration_hours
        )

        # Adjust for quality metrics
        quality_bonus = 0.0
        if self.metrics.tests_added > 0:
            quality_bonus += 0.1
        if self.metrics.bugs_fixed > 0:
            quality_bonus += 0.05

        # Penalty for retries
        retry_penalty = self.retry_count * 0.1

        return max(0.0, min(2.0, time_efficiency + quality_bonus - retry_penalty))
