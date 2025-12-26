#!/usr/bin/env python3
"""
Checkpoint Data Model.

Strongly-typed model for checkpoint data in ONEX storage backends.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_checkpoint_status import EnumCheckpointStatus
from omnibase_core.enums.enum_checkpoint_type import EnumCheckpointType
from omnibase_core.models.core.model_storage_checkpoint_metadata import (
    ModelStorageCheckpointMetadata,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCheckpointData(BaseModel):
    """
    Model for checkpoint data in ONEX storage systems.

    Used by storage backends to persist and restore workflow state
    with comprehensive metadata and versioning support.
    """

    checkpoint_id: UUID = Field(description="Unique checkpoint identifier")

    workflow_id: UUID = Field(description="Associated workflow identifier")

    checkpoint_type: EnumCheckpointType = Field(
        description="Type of checkpoint",
    )

    status: EnumCheckpointStatus = Field(
        description="Current status of the checkpoint",
        default=EnumCheckpointStatus.ACTIVE,
    )

    data_payload: "SerializedDict" = Field(
        description="Serialized checkpoint data payload",
        default_factory=dict,
    )

    metadata: ModelStorageCheckpointMetadata | None = Field(
        default=None,
        description="Typed metadata for checkpoint categorization and organization",
    )

    created_at: datetime = Field(
        description="When the checkpoint was created",
        default_factory=datetime.now,
    )

    updated_at: datetime = Field(
        description="When the checkpoint was last updated",
        default_factory=datetime.now,
    )

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Checkpoint data format version",
    )

    size_bytes: int = Field(
        description="Size of checkpoint data in bytes",
        default=0,
    )

    checksum: str = Field(
        description="Data integrity checksum",
        default="",
    )
