"""Model for Claude Code agent task assignment and tracking."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.models.ai_workflows.model_task_metadata import ModelTaskMetadata


class EnumTaskPriority(str, Enum):
    """Task priority levels for agent assignment."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnumTaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnumTaskType(str, Enum):
    """Types of tasks agents can perform."""

    CODE_IMPROVEMENT = "code_improvement"
    BUG_FIX = "bug_fix"
    FEATURE_IMPLEMENTATION = "feature_implementation"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY_FIX = "security_fix"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class ModelAgentTask(BaseModel):
    """
    Task assignment for Claude Code agents.

    Represents a unit of work that can be assigned to an agent,
    tracked through execution, and coordinated with other tasks.
    """

    task_id: str = Field(description="Unique identifier for the task")

    task_type: EnumTaskType = Field(description="Type of task to be performed")

    title: str = Field(description="Human-readable task title", max_length=200)

    description: str = Field(description="Detailed task description with requirements")

    work_ticket_id: str | None = Field(
        default=None,
        description="Associated work ticket ID if applicable",
    )

    branch_name: str = Field(description="Git branch name for isolated work")

    priority: EnumTaskPriority = Field(
        default=EnumTaskPriority.MEDIUM,
        description="Task priority for scheduling",
    )

    status: EnumTaskStatus = Field(
        default=EnumTaskStatus.PENDING,
        description="Current task status",
    )

    assigned_agent_id: str | None = Field(
        default=None,
        description="ID of agent assigned to this task",
    )

    context_files: list[str] = Field(
        default_factory=list,
        description="Files to include in agent context",
    )

    target_files: list[str] = Field(
        default_factory=list,
        description="Specific files to be modified",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="Task IDs that must complete before this task",
    )

    estimated_duration_minutes: int = Field(
        default=30,
        description="Estimated time to complete in minutes",
        ge=5,
        le=480,  # Max 8 hours
    )

    # Container isolation settings
    isolation_level: str = Field(
        default="thread",
        description="Isolation level (thread, process, container)",
    )

    docker_image: str | None = Field(
        default=None,
        description="Docker image for container isolation (if isolation_level=container)",
    )

    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for task execution",
    )

    metadata: ModelTaskMetadata = Field(
        default_factory=ModelTaskMetadata,
        description="Additional task-specific metadata",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation timestamp",
    )

    assigned_at: datetime | None = Field(
        default=None,
        description="When task was assigned to agent",
    )

    started_at: datetime | None = Field(
        default=None,
        description="When agent started working on task",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When task was completed",
    )

    def to_agent_prompt(self) -> str:
        """Generate a detailed prompt for the agent."""
        prompt_parts = [
            f"# Task: {self.title}",
            f"Task ID: {self.task_id}",
            f"Type: {self.task_type.value}",
            f"Priority: {self.priority.value}",
            "",
            "## Description",
            self.description,
            "",
            "## Requirements",
            "- Follow all ONEX standards and patterns",
            "- Use strong typing (no Any types)",
            "- Handle errors with OnexError",
            "- Create comprehensive tests",
            "- Update documentation as needed",
        ]

        if self.work_ticket_id:
            prompt_parts.extend(
                [
                    "",
                    f"## Work Ticket: {self.work_ticket_id}",
                ],
            )

        if self.target_files:
            prompt_parts.extend(
                [
                    "",
                    "## Target Files",
                    *[f"- {file}" for file in self.target_files],
                ],
            )

        if self.context_files:
            prompt_parts.extend(
                [
                    "",
                    "## Context Files",
                    *[f"- {file}" for file in self.context_files],
                ],
            )

        prompt_parts.extend(
            [
                "",
                f"## Working Branch: {self.branch_name}",
                "",
                "Begin implementation following ONEX standards.",
            ],
        )

        return "\n".join(prompt_parts)

    def to_event_data(self) -> dict:
        """Convert to event-compatible dictionary format."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "title": self.title,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_agent_id": self.assigned_agent_id,
            "branch_name": self.branch_name,
            "work_ticket_id": self.work_ticket_id,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "isolation_level": self.isolation_level,
            "docker_image": self.docker_image,
            "environment_variables": dict(self.environment_variables),
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
