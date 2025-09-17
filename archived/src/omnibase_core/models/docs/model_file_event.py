"""File Event model generated from contract."""

from datetime import datetime
from typing import Any, Union

from pydantic import BaseModel, Field

# REMOVED: Type alias patterns violate ONEX strong typing standards
# REPLACED with proper Pydantic model below


class ModelFileEventMetadata(BaseModel):
    """
    Strongly-typed metadata for file system events.

    Replaces FileEventMetadata dict alias with proper Pydantic model
    providing runtime validation and type safety.

    ZERO TOLERANCE: No Any types or dict patterns allowed.
    """

    # Common metadata fields
    permissions: str | None = Field(
        default=None,
        description="File permissions in octal format",
        pattern=r"^[0-7]{3,4}$",
    )

    owner: str | None = Field(
        default=None,
        description="File owner username",
        max_length=100,
    )

    group: str | None = Field(
        default=None,
        description="File group name",
        max_length=100,
    )

    mime_type: str | None = Field(
        default=None,
        description="MIME type of the file",
        max_length=200,
    )

    encoding: str | None = Field(
        default=None,
        description="File encoding (e.g., 'utf-8')",
        max_length=50,
    )

    # Process information
    process_id: int | None = Field(
        default=None,
        description="Process ID that triggered the event",
        ge=1,
    )

    process_name: str | None = Field(
        default=None,
        description="Name of process that triggered the event",
        max_length=255,
    )

    # Additional flags
    is_directory: bool = Field(
        default=False,
        description="Whether the target is a directory",
    )

    is_hidden: bool = Field(
        default=False,
        description="Whether the file is hidden",
    )

    is_executable: bool = Field(
        default=False,
        description="Whether the file is executable",
    )

    # Custom attributes for flexibility (strongly typed)
    tags: list[str] = Field(
        default_factory=list,
        description="Custom tags associated with the event",
    )

    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Additional string-based attributes",
    )

    numeric_attributes: dict[str, int | float] = Field(
        default_factory=dict,
        description="Additional numeric attributes",
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        extra = "forbid"  # Reject additional fields for strict typing
        validate_assignment = True


class model_file_event(BaseModel):
    """Model representing a filesystem event with metadata."""

    event_id: str = Field(
        ...,
        description="Unique identifier for the event",
        min_length=1,
        max_length=255,
    )

    event_type: str = Field(..., description="Type of filesystem event")

    file_path: str = Field(
        ...,
        description="Absolute path to the affected file",
        min_length=1,
        max_length=4096,
    )

    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the event occurred",
    )

    checksum: str | None = Field(
        default=None,
        description="SHA-256 checksum of the file content (for files)",
        pattern=r"^[a-f0-9]{64}$",
    )

    file_size: int | None = Field(
        default=None,
        description="Size of the file in bytes",
        ge=0,
    )

    old_path: str | None = Field(
        default=None,
        description="Previous path for move/rename operations",
        min_length=1,
        max_length=4096,
    )

    metadata: ModelFileEventMetadata | None = Field(
        default=None,
        description="Additional event metadata with strong typing",
    )

    is_directory: bool = Field(
        default=False,
        description="Whether the path represents a directory",
    )
