"""Sync Status model generated from contract."""

from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

# Type alias for metadata instead of Dict[str, Any]
SyncMetadataValue = Union[str, int, float, bool, list[str]]
SyncMetadata = dict[str, SyncMetadataValue]


class model_sync_status(BaseModel):
    """Model representing the synchronization status of a file or directory."""

    sync_id: str = Field(
        ...,
        description="Unique identifier for the sync operation",
        min_length=1,
        max_length=255,
    )

    path: str = Field(
        ...,
        description="Absolute path being synchronized",
        min_length=1,
        max_length=4096,
    )

    status: str = Field(..., description="Current synchronization status")

    last_updated: datetime = Field(
        ...,
        description="ISO 8601 timestamp of last status update",
    )

    last_checksum: str | None = Field(
        default=None,
        description="Last known SHA-256 checksum",
        pattern=r"^[a-f0-9]{64}$",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if sync failed",
        max_length=1024,
    )

    retry_count: int = Field(default=0, description="Number of retry attempts", ge=0)

    priority: int = Field(
        default=5,
        description="Sync priority (higher values = higher priority)",
        ge=1,
        le=10,
    )

    created_at: datetime = Field(
        ...,
        description="ISO 8601 timestamp when sync was created",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="ISO 8601 timestamp when sync completed",
    )

    metadata: SyncMetadata | None = Field(
        default=None,
        description="Additional sync metadata",
    )
