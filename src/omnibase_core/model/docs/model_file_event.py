"""File Event model generated from contract."""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Type alias for metadata instead of Dict[str, Any]
FileEventMetadataValue = Union[str, int, float, bool, List[str]]
FileEventMetadata = Dict[str, FileEventMetadataValue]


class model_file_event(BaseModel):
    """Model representing a filesystem event with metadata."""

    event_id: str = Field(
        ..., description="Unique identifier for the event", min_length=1, max_length=255
    )

    event_type: str = Field(..., description="Type of filesystem event")

    file_path: str = Field(
        ...,
        description="Absolute path to the affected file",
        min_length=1,
        max_length=4096,
    )

    timestamp: datetime = Field(
        ..., description="ISO 8601 timestamp when the event occurred"
    )

    checksum: Optional[str] = Field(
        default=None,
        description="SHA-256 checksum of the file content (for files)",
        pattern=r"^[a-f0-9]{64}$",
    )

    file_size: Optional[int] = Field(
        default=None, description="Size of the file in bytes", ge=0
    )

    old_path: Optional[str] = Field(
        default=None,
        description="Previous path for move/rename operations",
        min_length=1,
        max_length=4096,
    )

    metadata: Optional[FileEventMetadata] = Field(
        default=None, description="Additional event metadata"
    )

    is_directory: bool = Field(
        default=False, description="Whether the path represents a directory"
    )
