"""
Database Conflict Data Model for Intelligence File Stamps.

Represents conflict resolution data when database and file stamps are inconsistent.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class model_database_conflict_data(BaseModel):
    """
    Model representing database sync conflict information.

    Used when file stamps and database records are inconsistent,
    providing details for conflict resolution.
    """

    conflict_type: str = Field(
        ...,
        description="Type of conflict: hash_mismatch, timestamp_conflict, missing_record, corrupted_stamp",
    )

    file_hash_expected: str = Field(
        ..., description="Expected BLAKE3 hash from file content"
    )

    file_hash_actual: Optional[str] = Field(
        None, description="Actual hash from file stamp"
    )

    database_hash: Optional[str] = Field(None, description="Hash stored in database")

    file_timestamp: Optional[datetime] = Field(
        None, description="Timestamp from file stamp"
    )

    database_timestamp: Optional[datetime] = Field(
        None, description="Timestamp from database record"
    )

    resolution_strategy: str = Field(
        ...,
        description="Conflict resolution strategy: prefer_file, prefer_database, manual_review",
    )

    file_uid: Optional[UUID] = Field(None, description="File unique identifier")

    detected_at: datetime = Field(..., description="When the conflict was detected")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
    )
