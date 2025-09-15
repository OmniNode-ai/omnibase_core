"""Sync Status model generated from contract."""

from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

# REMOVED: Type alias patterns violate ONEX strong typing standards
# REPLACED with proper Pydantic model below


class ModelSyncMetadata(BaseModel):
    """
    Strongly-typed metadata for synchronization operations.

    Replaces SyncMetadata dict alias with proper Pydantic model
    providing runtime validation and type safety.

    ZERO TOLERANCE: No Any types or dict patterns allowed.
    """

    # Source information
    source_host: str | None = Field(
        default=None,
        description="Source hostname for sync operation",
        max_length=255,
    )

    source_path: str | None = Field(
        default=None,
        description="Source path for sync operation",
        max_length=4096,
    )

    # Destination information
    destination_host: str | None = Field(
        default=None,
        description="Destination hostname for sync operation",
        max_length=255,
    )

    destination_path: str | None = Field(
        default=None,
        description="Destination path for sync operation",
        max_length=4096,
    )

    # Performance metrics
    bytes_transferred: int | None = Field(
        default=None,
        description="Number of bytes transferred",
        ge=0,
    )

    transfer_rate_mbps: float | None = Field(
        default=None,
        description="Transfer rate in megabits per second",
        ge=0,
    )

    # Operation details
    operation_type: str | None = Field(
        default=None,
        description="Type of sync operation (copy, move, delete, etc.)",
        max_length=50,
    )

    conflict_resolution: str | None = Field(
        default=None,
        description="How conflicts were resolved",
        max_length=100,
    )

    # User information
    initiated_by_user: str | None = Field(
        default=None,
        description="Username who initiated the sync",
        max_length=100,
    )

    initiated_by_process: str | None = Field(
        default=None,
        description="Process name that initiated the sync",
        max_length=255,
    )

    # Flags
    is_incremental: bool = Field(
        default=False,
        description="Whether this is an incremental sync",
    )

    requires_authentication: bool = Field(
        default=False,
        description="Whether sync requires authentication",
    )

    # Additional attributes (strongly typed)
    tags: list[str] = Field(
        default_factory=list,
        description="Custom tags for categorization",
    )

    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Additional string-based metadata",
    )

    numeric_attributes: dict[str, int | float] = Field(
        default_factory=dict,
        description="Additional numeric metadata",
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        extra = "forbid"  # Reject additional fields for strict typing
        validate_assignment = True


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

    metadata: ModelSyncMetadata | None = Field(
        default=None,
        description="Additional sync metadata with strong typing",
    )
