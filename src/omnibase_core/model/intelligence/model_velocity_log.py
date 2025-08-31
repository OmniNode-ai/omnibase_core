"""
Pydantic model for velocity logs in the direct knowledge pipeline.

This model represents development velocity and productivity metrics
that are written directly to the PostgreSQL database bypassing repository.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelVelocityLog(BaseModel):
    """
    Development velocity log entry for productivity tracking.

    Maps to debug_intelligence.velocity_logs table in PostgreSQL.
    Used for direct-to-database writes bypassing repository.
    """

    velocity_id: str = Field(
        ...,
        description="Unique identifier for this velocity log entry",
    )

    agent_id: str = Field(..., description="Agent that performed the development work")

    task_description: str = Field(
        ...,
        description="Description of the task or work completed",
    )

    task_type: str = Field(
        ...,
        description="Type of task: implementation, debugging, analysis, documentation",
    )

    # Timing metrics
    started_at: datetime = Field(..., description="When the task was started")

    completed_at: datetime = Field(..., description="When the task was completed")

    duration_seconds: float = Field(
        ...,
        description="Task duration in seconds (calculated automatically)",
    )

    # Velocity metrics
    lines_of_code_changed: int = Field(
        default=0,
        description="Number of lines of code modified",
    )

    files_modified: int = Field(default=0, description="Number of files modified")

    tools_used: list[str] = Field(
        default_factory=list,
        description="List of tools used during task execution",
    )

    success: bool = Field(..., description="Whether the task completed successfully")

    # Quality metrics
    complexity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Task complexity score from 0.0-1.0",
    )

    effectiveness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Agent effectiveness score from 0.0-1.0",
    )

    # Context and metadata
    work_session_id: str | None = Field(
        default=None,
        description="ID of the work session this task belongs to",
    )

    branch_name: str | None = Field(
        default=None,
        description="Git branch where work was performed",
    )

    commit_hash: str | None = Field(
        default=None,
        description="Git commit hash of completed work",
    )

    # JSON data for extensibility
    metrics: dict = Field(
        default_factory=dict,
        description="Additional metrics data as JSON",
    )

    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata as JSON",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was last updated",
    )

    class Config:
        """Pydantic configuration for the velocity log model."""

        # Enable JSON encoding for datetime objects
        json_encoders = {datetime: lambda v: v.isoformat()}

        # Allow extra fields for future extensibility
        extra = "forbid"

        # Validate assignment to catch errors early
        validate_assignment = True

        # Use enum values for string enums
        use_enum_values = True
