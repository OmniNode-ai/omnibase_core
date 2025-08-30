"""
Atomic Rollback Data Model for Intelligence File Operations.

Represents rollback information for atomic file operations.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class model_atomic_rollback_data(BaseModel):
    """
    Model representing rollback data for atomic file operations.

    Contains backup information needed to restore files to previous state
    if an atomic operation fails partway through.
    """

    operation_id: str = Field(..., description="Unique operation identifier")

    original_file_contents: dict[str, str] = Field(
        ...,
        description="Mapping of file paths to their original content",
    )

    backup_file_paths: dict[str, str] = Field(
        ...,
        description="Mapping of original paths to backup file locations",
    )

    created_files: list[str] = Field(
        default_factory=list,
        description="List of new files created during operation",
    )

    modified_files: list[str] = Field(
        default_factory=list,
        description="List of existing files that were modified",
    )

    file_permissions: dict[str, int] = Field(
        default_factory=dict,
        description="Original file permissions (octal mode)",
    )

    operation_start_time: datetime = Field(..., description="When the operation began")

    rollback_reason: str | None = Field(
        None,
        description="Reason for rollback if operation failed",
    )

    is_rolled_back: bool = Field(
        False,
        description="Whether rollback has been executed",
    )

    rollback_completed_at: datetime | None = Field(
        None,
        description="When rollback was completed",
    )

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
