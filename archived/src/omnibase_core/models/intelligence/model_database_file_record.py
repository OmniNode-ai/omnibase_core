"""
Database File Record Model for Intelligence File Stamps.

Represents file metadata records as stored in PostgreSQL database.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class model_database_file_record(BaseModel):
    """
    Model representing a file metadata record from the database.

    Maps PostgreSQL file_metadata table structure to strongly-typed model.
    """

    file_path: str = Field(..., description="Absolute file path")

    file_uid: UUID = Field(..., description="Unique file identifier")

    content_hash: str = Field(..., description="BLAKE3 content hash")

    hash_algorithm: str = Field(..., description="Hash algorithm used (BLAKE3)")

    file_size: int = Field(..., description="File size in bytes")

    language: str | None = Field(None, description="Detected programming language")

    comment_style: str | None = Field(
        None,
        description="Comment style used for stamps",
    )

    stamp_format: str = Field(..., description="Stamp format version")

    created_at: datetime = Field(..., description="Record creation timestamp")

    updated_at: datetime = Field(..., description="Last update timestamp")

    version: int = Field(..., description="Record version for conflict resolution")

    is_deleted: bool = Field(False, description="Soft deletion flag")

    intelligence_metadata: str | None = Field(
        None,
        description="JSON-encoded intelligence metadata",
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)},
    )
