"""
Model for work tickets in the ONEX system.

This model represents work items that can be assigned to Claude Code agents
for execution, including task details, dependencies, and requirements.
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class WorkTicketPriority(str, Enum):
    """Work ticket priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class WorkTicketStatus(str, Enum):
    """Work ticket status enumeration."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkTicketType(str, Enum):
    """Work ticket type enumeration."""

    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MAINTENANCE = "maintenance"
    RESEARCH = "research"
    DEPLOYMENT = "deployment"


class ModelWorkDependency(BaseModel):
    """Work dependency specification."""

    ticket_id: str = Field(description="ID of the dependent ticket")
    dependency_type: str = Field(
        description="Type of dependency (blocks, requires, follows)",
    )
    required: bool = Field(
        default=True,
        description="Whether this dependency is required",
    )
    description: str | None = Field(
        default=None,
        description="Description of the dependency relationship",
    )


class ModelWorkRequirement(BaseModel):
    """Work requirement specification."""

    requirement_id: str = Field(description="Unique identifier for this requirement")
    description: str = Field(description="Detailed requirement description")
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="List of acceptance criteria",
    )
    validation_method: str | None = Field(
        default=None,
        description="Method to validate this requirement",
    )
    priority: WorkTicketPriority = Field(
        default=WorkTicketPriority.MEDIUM,
        description="Priority of this requirement",
    )


class ModelWorkConstraint(BaseModel):
    """Work constraint specification."""

    constraint_type: str = Field(
        description="Type of constraint (time, resource, technical)",
    )
    description: str = Field(description="Constraint description")
    value: str | int | float | None = Field(
        default=None,
        description="Constraint value or limit",
    )
    enforcement_level: str = Field(
        default="strict",
        description="How strictly to enforce (strict, flexible, advisory)",
    )


class ModelWorkTicket(BaseModel):
    """Work ticket for Claude Code agent assignment."""

    ticket_id: str = Field(description="Unique identifier for this work ticket")
    title: str = Field(description="Short, descriptive title of the work")
    description: str = Field(description="Detailed description of the work to be done")
    ticket_type: WorkTicketType = Field(description="Type of work ticket")
    priority: WorkTicketPriority = Field(
        default=WorkTicketPriority.MEDIUM,
        description="Priority level of this ticket",
    )
    status: WorkTicketStatus = Field(
        default=WorkTicketStatus.PENDING,
        description="Current status of the ticket",
    )
    assigned_agent_id: str | None = Field(
        default=None,
        description="ID of the agent assigned to this ticket",
    )
    created_by: str = Field(description="User or system that created this ticket")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Ticket creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )
    assigned_at: datetime | None = Field(
        default=None,
        description="Assignment timestamp",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Work start timestamp",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Work completion timestamp",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Due date for completion",
    )
    estimated_hours: float | None = Field(
        default=None,
        description="Estimated hours to complete",
    )
    actual_hours: float | None = Field(
        default=None,
        description="Actual hours spent",
    )
    requirements: list[ModelWorkRequirement] = Field(
        default_factory=list,
        description="List of work requirements",
    )
    dependencies: list[ModelWorkDependency] = Field(
        default_factory=list,
        description="List of ticket dependencies",
    )
    constraints: list[ModelWorkConstraint] = Field(
        default_factory=list,
        description="List of work constraints",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and filtering",
    )
    affected_files: list[str] = Field(
        default_factory=list,
        description="List of files expected to be affected",
    )
    test_requirements: list[str] = Field(
        default_factory=list,
        description="List of testing requirements",
    )
    validation_steps: list[str] = Field(
        default_factory=list,
        description="Steps to validate completion",
    )
    rollback_plan: str | None = Field(
        default=None,
        description="Plan for rolling back if needed",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Additional notes and comments",
    )
    attachments: list[str] = Field(
        default_factory=list,
        description="List of attachment file paths",
    )
    context_data: dict[str, str] | None = Field(
        default=None,
        description="Additional context data",
    )
    agent_requirements: dict[str, str] | None = Field(
        default=None,
        description="Specific agent capability requirements",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if ticket failed",
    )
    progress_percent: float = Field(
        default=0.0,
        description="Progress percentage (0-100)",
    )
    session_id: str | None = Field(
        default=None,
        description="Session identifier for tracking",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for related events",
    )

    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue."""
        return (
            self.due_date is not None
            and datetime.now() > self.due_date
            and self.status
            not in [WorkTicketStatus.COMPLETED, WorkTicketStatus.CANCELLED]
        )

    @property
    def is_blocked(self) -> bool:
        """Check if ticket is blocked."""
        return self.status == WorkTicketStatus.BLOCKED

    @property
    def is_assigned(self) -> bool:
        """Check if ticket is assigned to an agent."""
        return self.assigned_agent_id is not None

    @property
    def is_in_progress(self) -> bool:
        """Check if ticket is currently being worked on."""
        return self.status == WorkTicketStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """Check if ticket is completed."""
        return self.status == WorkTicketStatus.COMPLETED

    @property
    def elapsed_time(self) -> timedelta | None:
        """Get elapsed time since work started."""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return end_time - self.started_at
        return None

    @property
    def time_to_completion(self) -> timedelta | None:
        """Get time from creation to completion."""
        if self.completed_at:
            return self.completed_at - self.created_at
        return None

    @property
    def pending_dependencies(self) -> list[str]:
        """Get list of pending dependency ticket IDs."""
        return [
            dep.ticket_id
            for dep in self.dependencies
            if dep.required and dep.dependency_type in ["blocks", "requires"]
        ]

    @property
    def critical_requirements(self) -> list[ModelWorkRequirement]:
        """Get list of critical requirements."""
        return [
            req
            for req in self.requirements
            if req.priority in [WorkTicketPriority.CRITICAL, WorkTicketPriority.URGENT]
        ]

    @property
    def is_urgent(self) -> bool:
        """Check if ticket has urgent priority."""
        return self.priority in [WorkTicketPriority.CRITICAL, WorkTicketPriority.URGENT]

    def add_note(self, note: str) -> None:
        """Add a note to the ticket."""
        timestamp = datetime.now().isoformat()
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.now()

    def update_progress(self, percent: float, note: str | None = None) -> None:
        """Update progress percentage."""
        self.progress_percent = max(0.0, min(100.0, percent))
        self.updated_at = datetime.now()
        if note:
            self.add_note(f"Progress: {percent}% - {note}")

    def assign_to_agent(self, agent_id: str) -> None:
        """Assign ticket to an agent."""
        self.assigned_agent_id = agent_id
        self.assigned_at = datetime.now()
        self.status = WorkTicketStatus.ASSIGNED
        self.updated_at = datetime.now()
        self.add_note(f"Assigned to agent {agent_id}")

    def start_work(self) -> None:
        """Mark ticket as in progress."""
        self.status = WorkTicketStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.updated_at = datetime.now()
        self.add_note("Work started")

    def complete_work(
        self,
        success: bool = True,
        message: str | None = None,
    ) -> None:
        """Mark ticket as completed."""
        self.status = WorkTicketStatus.COMPLETED if success else WorkTicketStatus.FAILED
        self.completed_at = datetime.now()
        self.progress_percent = 100.0 if success else self.progress_percent
        self.updated_at = datetime.now()

        note = f"Work {'completed successfully' if success else 'failed'}"
        if message:
            note += f": {message}"
        self.add_note(note)

        if not success and message:
            self.error_message = message
