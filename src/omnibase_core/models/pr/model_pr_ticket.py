"""
PR Ticket Model for tracking pull request creation and metadata.

This model represents a pull request ticket with UUID tracking,
file modifications, and agent actions using strong typing.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.ai_workflows.model_ai_execution_metrics import (
    EnumMetricType,
    EnumMetricUnit,
    ModelMetricValue,
)
from omnibase_core.models.core.model_tool_type import ModelToolType


class EnumFileModificationType(str, Enum):
    """Types of file modifications in a PR."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    MOVED = "moved"


class EnumAgentActionType(str, Enum):
    """Types of agent actions during PR creation."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    COMMIT = "commit"


class EnumPrStatus(str, Enum):
    """PR status values."""

    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    MERGED = "merged"
    CLOSED = "closed"


class ModelPrFileModification(BaseModel):
    """Represents a single file modification in a PR with UUID tracking."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    file_path: Path = Field(description="Path to the modified file")
    file_uuid: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking this file",
    )
    lines_added: int = Field(ge=0, description="Number of lines added")
    lines_removed: int = Field(ge=0, description="Number of lines removed")
    modification_type: EnumFileModificationType = Field(
        description="Type of modification",
    )
    content_hash: str = Field(
        description="Content hash for change detection",
        min_length=1,
    )


class ModelPrToolCall(BaseModel):
    """Represents a tool call that contributed to PR changes."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    tool_type: ModelToolType = Field(description="Type of tool that was called")
    call_timestamp: datetime = Field(description="When the tool was called")
    input_parameters: dict[str, Any] = Field(description="Tool input parameters")
    output_result: dict[str, Any] = Field(description="Tool output result")
    affected_files: list[Path] = Field(description="Files affected by this tool call")
    success: bool = Field(description="Whether the tool call was successful")


class ModelPrAgentAction(BaseModel):
    """Represents an agent action during PR creation."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique action identifier",
    )
    action_type: EnumAgentActionType = Field(description="Type of action performed")
    description: str = Field(
        description="Human-readable action description",
        min_length=1,
    )
    timestamp: datetime = Field(description="When the action was performed")
    confidence_score: ModelMetricValue = Field(
        description="Agent confidence in this action",
    )
    reasoning: dict[str, Any] = Field(description="Agent's reasoning for this action")


class ModelPrTicket(BaseModel):
    """
    Complete PR ticket model with UUID tracking and agent metadata.

    This model captures all aspects of PR creation including file changes,
    tool usage, agent actions, and tree structure changes.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    # Primary identification
    pr_ticket_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique PR ticket identifier",
    )
    agent_id: str = Field(description="ID of the agent creating the PR", min_length=1)

    # PR information
    pr_number: int = Field(
        default=0,
        ge=0,
        description="GitHub PR number (0 if not yet created)",
    )
    pr_title: str = Field(description="Title of the pull request", min_length=1)
    pr_description: str = Field(description="Detailed PR description", min_length=1)
    pr_branch: str = Field(description="Branch name for the PR", min_length=1)

    # File tracking with strong typing
    modified_files: list[ModelPrFileModification] = Field(
        default_factory=list,
        description="List of files modified with UUID tracking",
    )

    # Tree structure tracking
    tree_structure_before: dict[str, Any] = Field(
        default_factory=dict,
        description="Repository tree structure before changes",
    )
    tree_structure_after: dict[str, Any] = Field(
        default_factory=dict,
        description="Repository tree structure after changes",
    )

    # Change analysis with metrics
    total_files_changed: int = Field(
        default=0,
        ge=0,
        description="Total number of files changed",
    )
    total_lines_added: int = Field(default=0, ge=0, description="Total lines added")
    total_lines_removed: int = Field(default=0, ge=0, description="Total lines removed")

    change_complexity: ModelMetricValue = Field(
        default_factory=lambda: ModelMetricValue(
            name="pr_complexity",
            value=0.0,
            unit=EnumMetricUnit.SCORE_0_TO_1,
            type=EnumMetricType.QUALITY,
        ),
        description="PR complexity metric",
    )

    # Tool and agent correlation
    tool_calls: list[ModelPrToolCall] = Field(
        default_factory=list,
        description="List of tool calls that led to file modifications",
    )

    agent_actions: list[ModelPrAgentAction] = Field(
        default_factory=list,
        description="List of agent actions during PR creation",
    )

    # Status and lifecycle
    status: EnumPrStatus = Field(default=EnumPrStatus.DRAFT, description="PR status")
    merged_at: datetime | None = Field(
        default=None,
        description="When the PR was merged",
    )
    closed_at: datetime | None = Field(
        default=None,
        description="When the PR was closed",
    )

    # Extensible metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for extensibility",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record last update timestamp",
    )
