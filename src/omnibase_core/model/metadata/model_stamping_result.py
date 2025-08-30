"""
Model for file stamping operation results.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from .model_file_info import ModelFileInfo
from .model_metadata_properties import ModelMetadataProperties


class EnumStampingOperation(str, Enum):
    """Stamping operations."""

    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    VALIDATE = "validate"


class EnumStampingStatus(str, Enum):
    """Stamping operation status."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class ModelStampingResult(BaseModel):
    """Model representing the result of a file stamping operation."""

    operation: EnumStampingOperation = Field(
        ..., description="Type of stamping operation performed"
    )

    status: EnumStampingStatus = Field(
        ..., description="Status of the stamping operation"
    )

    file_info: ModelFileInfo = Field(
        ..., description="Information about the file that was processed"
    )

    lines_added: int = Field(0, description="Number of lines added to the file")

    lines_removed: int = Field(0, description="Number of lines removed from the file")

    lines_modified: int = Field(0, description="Number of lines modified in the file")

    metadata_location: Optional[str] = Field(
        None, description="Location where metadata was placed (line numbers, etc.)"
    )

    backup_created: bool = Field(False, description="Whether a backup file was created")

    backup_path: Optional[str] = Field(
        None, description="Path to backup file if created"
    )

    processing_time_ms: float = Field(
        ..., description="Time taken for the operation in milliseconds"
    )

    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the operation was completed"
    )

    warnings: List[str] = Field(
        default_factory=list, description="Warning messages from the operation"
    )

    errors: List[str] = Field(
        default_factory=list, description="Error messages from the operation"
    )

    metadata: Optional[ModelMetadataProperties] = Field(
        None, description="Additional operation metadata"
    )

    content_before_hash: Optional[str] = Field(
        None, description="Hash of file content before operation"
    )

    content_after_hash: Optional[str] = Field(
        None, description="Hash of file content after operation"
    )
