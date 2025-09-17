"""
Pydantic model for PR tickets in the direct knowledge pipeline.

This model represents PR descriptions with UUID tracking and tree information
that are written directly to the PostgreSQL database bypassing repository.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelFileChange(BaseModel):
    """
    Represents a file modification with UUID tracking.
    """

    file_path: str = Field(..., description="Path to the modified file")

    file_uuid: str = Field(..., description="UUID assigned to this file for tracking")

    change_type: str = Field(
        ...,
        description="Type of change: added, modified, deleted, renamed",
    )

    lines_added: int = Field(
        default=0,
        description="Number of lines added to this file",
    )

    lines_removed: int = Field(
        default=0,
        description="Number of lines removed from this file",
    )

    complexity_delta: float = Field(
        default=0.0,
        description="Change in complexity score for this file",
    )


class ModelToolCall(BaseModel):
    """
    Represents a tool call linked to file modifications.
    """

    tool_name: str = Field(..., description="Name of the tool that was called")

    timestamp: datetime = Field(..., description="When the tool was called")

    affected_files: list[str] = Field(
        default_factory=list,
        description="List of file UUIDs affected by this tool call",
    )

    tool_result: str = Field(
        default="",
        description="Result or output from the tool call",
    )

    success: bool = Field(..., description="Whether the tool call was successful")


class ModelAgentAction(BaseModel):
    """
    Represents an agent action linked to PR creation.
    """

    action_type: str = Field(
        ...,
        description="Type of action: file_read, file_write, analysis, decision",
    )

    timestamp: datetime = Field(..., description="When the action was performed")

    affected_files: list[str] = Field(
        default_factory=list,
        description="List of file UUIDs affected by this action",
    )

    reasoning: str = Field(default="", description="Agent's reasoning for this action")

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in this action",
    )


class ModelPrTicket(BaseModel):
    """
    PR ticket with UUID tracking and tree information.

    Maps to debug_intelligence.pr_tickets table in PostgreSQL.
    Used for direct-to-database writes bypassing repository.
    """

    pr_ticket_id: str = Field(..., description="Unique identifier for this PR ticket")

    agent_id: str = Field(..., description="Agent that created this PR")

    # PR identification
    pr_number: int | None = Field(
        default=None,
        description="GitHub PR number (if PR has been created)",
    )

    pr_title: str = Field(..., description="Title of the PR")

    pr_description: str = Field(..., description="Detailed description of the PR")

    pr_branch: str = Field(..., description="Git branch for this PR")

    # File tracking with UUIDs
    modified_files: list[ModelFileChange] = Field(
        default_factory=list,
        description="Array of file objects with UUIDs for tracking",
    )

    tree_structure_before: dict = Field(
        default_factory=dict,
        description="Directory tree structure before changes",
    )

    tree_structure_after: dict = Field(
        default_factory=dict,
        description="Directory tree structure after changes",
    )

    # Change analysis
    total_files_changed: int = Field(
        default=0,
        description="Total number of files modified",
    )

    total_lines_added: int = Field(
        default=0,
        description="Total lines added across all files",
    )

    total_lines_removed: int = Field(
        default=0,
        description="Total lines removed across all files",
    )

    change_complexity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall complexity of changes from 0.0-1.0",
    )

    # Tool correlation
    tool_calls: list[ModelToolCall] = Field(
        default_factory=list,
        description="Array of tool call objects linked to changes",
    )

    agent_actions: list[ModelAgentAction] = Field(
        default_factory=list,
        description="Array of agent action objects",
    )

    # Status and lifecycle
    status: str = Field(
        default="draft",
        description="PR status: draft, ready, submitted, merged, closed",
    )

    merged_at: datetime | None = Field(
        default=None,
        description="When the PR was merged",
    )

    closed_at: datetime | None = Field(
        default=None,
        description="When the PR was closed",
    )

    # Metadata
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
        """Pydantic configuration for the PR ticket model."""

        # Enable JSON encoding for datetime objects
        json_encoders = {datetime: lambda v: v.isoformat()}

        # Allow extra fields for future extensibility
        extra = "forbid"

        # Validate assignment to catch errors early
        validate_assignment = True

        # Use enum values for string enums
        use_enum_values = True
