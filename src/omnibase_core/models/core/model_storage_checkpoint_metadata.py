#!/usr/bin/env python3
"""
Storage Checkpoint Metadata Model.

Strongly-typed model for checkpoint metadata in ONEX storage backends.
Replaces dict[str, str] for type safety.

Note: This is distinct from ModelCheckpointMetadata in omnibase_core.models.context,
which is used for workflow state tracking. This model is specifically for
storage backend persistence metadata.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelStorageCheckpointMetadata"]


class ModelStorageCheckpointMetadata(BaseModel):
    """
    Typed metadata for checkpoint data in storage backends.

    Provides structured storage for checkpoint-related metadata,
    replacing untyped dict[str, str] usage for type safety.

    This model is used by storage backends (e.g., file system, S3, database)
    to persist checkpoint metadata alongside checkpoint payloads.

    Note: For workflow state checkpoint metadata, use
    omnibase_core.models.context.ModelCheckpointMetadata instead.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    source: str | None = Field(
        default=None,
        description="Source identifier for the checkpoint (e.g., node name, workflow step)",
    )

    environment: str | None = Field(
        default=None,
        description="Environment where checkpoint was created (e.g., dev, staging, prod)",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for organizing and filtering checkpoints",
    )

    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value labels for checkpoint categorization",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the checkpoint",
    )

    parent_checkpoint_id: str | None = Field(  # string-id-ok: checkpoint identifier
        default=None,
        description="ID of parent checkpoint if this is an incremental checkpoint",
    )

    retention_policy: str | None = Field(
        default=None,
        description="Retention policy identifier for cleanup scheduling",
    )
