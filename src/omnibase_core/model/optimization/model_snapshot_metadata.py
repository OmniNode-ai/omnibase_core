"""
Model for snapshot metadata.

Metadata for usage snapshot tracking.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelSnapshotMetadata(BaseModel):
    """Metadata for usage snapshot."""

    error_message: Optional[str] = Field(None, description="Error if task failed")
    retry_count: int = Field(0, description="Number of retries")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID if subtask")
