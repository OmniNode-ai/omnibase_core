"""
Model for work completion results from Claude Code agents.

This model represents the final result when an agent completes
a work task, including success status, files modified, and metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WorkResultStatus(str, Enum):
    """Work result status enumeration."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ModelFileChange(BaseModel):
    """Individual file change within work result."""

    file_path: str = Field(description="Path to the modified file")
    change_type: str = Field(
        description="Type of change (created, modified, deleted, renamed)"
    )
    lines_added: int = Field(default=0, description="Number of lines added")
    lines_removed: int = Field(default=0, description="Number of lines removed")
    checksum: Optional[str] = Field(
        default=None, description="File checksum after change"
    )
    backup_path: Optional[str] = Field(
        default=None, description="Path to backup of original file"
    )


class ModelValidationResult(BaseModel):
    """Validation result for work completion."""

    validator_name: str = Field(description="Name of the validator")
    passed: bool = Field(description="Whether validation passed")
    message: str = Field(description="Validation message or error details")
    execution_time_ms: float = Field(
        description="Time taken to run validation in milliseconds"
    )
    output: Optional[str] = Field(default=None, description="Validation output or logs")


class ModelWorkResult(BaseModel):
    """Work completion result from Claude Code agent."""

    result_id: str = Field(description="Unique identifier for this work result")
    agent_id: str = Field(description="ID of the agent that completed the work")
    task_id: str = Field(description="ID of the completed task")
    ticket_id: Optional[str] = Field(
        default=None, description="ID of the work ticket that was processed"
    )
    status: WorkResultStatus = Field(
        description="Overall status of the work completion"
    )
    success: bool = Field(description="Whether the work was completed successfully")
    message: str = Field(description="Human-readable completion message")
    files_changed: List[ModelFileChange] = Field(
        default_factory=list, description="List of files that were modified"
    )
    commands_executed: List[str] = Field(
        default_factory=list, description="List of commands that were executed"
    )
    validation_results: List[ModelValidationResult] = Field(
        default_factory=list, description="Results from validation checks"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if work failed"
    )
    error_details: Optional[Dict[str, str]] = Field(
        default=None, description="Additional error details"
    )
    execution_time_seconds: int = Field(description="Total execution time in seconds")
    start_time: datetime = Field(description="Work start timestamp")
    completion_time: datetime = Field(
        default_factory=datetime.now, description="Work completion timestamp"
    )
    resource_usage: Optional[Dict[str, float]] = Field(
        default=None, description="Resource usage during execution"
    )
    rollback_available: bool = Field(
        default=False, description="Whether rollback is available for this work"
    )
    rollback_data: Optional[Dict[str, str]] = Field(
        default=None, description="Data needed for rollback operation"
    )
    session_id: Optional[str] = Field(
        default=None, description="Agent session identifier"
    )
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracking related events"
    )
    artifacts: List[str] = Field(
        default_factory=list, description="List of artifact paths created during work"
    )
    test_results: Optional[Dict[str, bool]] = Field(
        default=None, description="Test execution results"
    )
    quality_metrics: Optional[Dict[str, float]] = Field(
        default=None, description="Code quality metrics"
    )

    @property
    def duration_seconds(self) -> int:
        """Calculate work duration in seconds."""
        if hasattr(self, "completion_time") and hasattr(self, "start_time"):
            return int((self.completion_time - self.start_time).total_seconds())
        return self.execution_time_seconds

    @property
    def files_created(self) -> List[str]:
        """Get list of files that were created."""
        return [
            change.file_path
            for change in self.files_changed
            if change.change_type == "created"
        ]

    @property
    def files_modified(self) -> List[str]:
        """Get list of files that were modified."""
        return [
            change.file_path
            for change in self.files_changed
            if change.change_type == "modified"
        ]

    @property
    def files_deleted(self) -> List[str]:
        """Get list of files that were deleted."""
        return [
            change.file_path
            for change in self.files_changed
            if change.change_type == "deleted"
        ]

    @property
    def total_lines_changed(self) -> int:
        """Get total number of lines changed."""
        return sum(
            change.lines_added + change.lines_removed for change in self.files_changed
        )

    @property
    def validation_passed(self) -> bool:
        """Check if all validations passed."""
        return all(result.passed for result in self.validation_results)

    @property
    def has_errors(self) -> bool:
        """Check if work result contains errors."""
        return self.status == WorkResultStatus.FAILED or self.error_message is not None

    @property
    def is_rollback_required(self) -> bool:
        """Check if rollback is required due to failures."""
        return (
            self.has_errors
            and self.rollback_available
            and self.status in [WorkResultStatus.FAILED, WorkResultStatus.TIMEOUT]
        )
