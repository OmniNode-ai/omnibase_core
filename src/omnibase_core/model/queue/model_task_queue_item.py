"""
ONEX-compliant model for task queue items.

Task queue model for scalable distributed task processing.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EnumTaskPriority(int, Enum):
    """Task priority enumeration."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class EnumTaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ModelTaskQueueItem(BaseModel):
    """
    Task queue item model for distributed task processing.

    Represents a task in the queue with proper scheduling, priority,
    and lifecycle management following ONEX standards.
    """

    task_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique task identifier",
    )
    task_type: str = Field(..., description="Type of task to be executed")
    agent_requirement: str | None = Field(
        None,
        description="Required agent capability or ID",
    )

    # Task scheduling
    priority: EnumTaskPriority = Field(
        EnumTaskPriority.NORMAL,
        description="Task priority level",
    )
    scheduled_at: datetime = Field(
        default_factory=datetime.now,
        description="When task was scheduled",
    )
    not_before: datetime | None = Field(
        None,
        description="Do not execute before this time",
    )
    expires_at: datetime | None = Field(None, description="Task expiration time")

    # Task lifecycle
    status: EnumTaskStatus = Field(
        EnumTaskStatus.PENDING,
        description="Current task status",
    )
    assigned_to: str | None = Field(
        None,
        description="Agent ID this task is assigned to",
    )
    assigned_at: datetime | None = Field(None, description="When task was assigned")
    started_at: datetime | None = Field(
        None,
        description="When task processing started",
    )
    completed_at: datetime | None = Field(
        None,
        description="When task was completed",
    )

    # Task execution
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: int = Field(60, description="Delay between retries in seconds")
    execution_timeout: int = Field(300, description="Task execution timeout in seconds")

    # Task data
    payload: dict[str, str | int | float | bool | dict | list] = Field(
        default_factory=dict,
        description="Task payload data with strongly typed values",
    )

    # Results and errors
    result: dict[str, str | int | float | bool | dict | list] | None = Field(
        None,
        description="Task result data",
    )
    error_message: str | None = Field(
        None,
        description="Error message if task failed",
    )
    error_code: str | None = Field(None, description="Error code if task failed")

    # Metadata
    created_by: str = Field(..., description="Entity that created this task")
    tags: dict[str, str] = Field(default_factory=dict, description="Task metadata tags")
    correlation_id: str | None = Field(
        None,
        description="Request correlation identifier",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_type": "code_review",
                "agent_requirement": "code_reviewer",
                "priority": 2,
                "scheduled_at": "2025-07-30T12:00:00Z",
                "status": "pending",
                "retry_count": 0,
                "max_retries": 3,
                "retry_delay": 60,
                "execution_timeout": 300,
                "payload": {
                    "code_content": "def hello(): return 'world'",
                    "language": "python",
                    "check_style": True,
                },
                "created_by": "user_123",
                "tags": {"environment": "production", "project": "omnibase"},
                "correlation_id": "req_abc123",
            },
        }
