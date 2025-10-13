"""
Storage List Result Model - ONEX Standards Compliant.

Strongly-typed model for storage backend list operation results.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_checkpoint_data import ModelCheckpointData

from .model_storage_list_result_config import ModelConfig


class ModelStorageListResult(BaseModel):
    """
    Model for storage backend list operation results.

    Used by storage backends to return paginated lists of
    checkpoints with metadata and pagination information.
    """

    success: bool = Field(description="Whether the list operation succeeded")

    checkpoints: list[ModelCheckpointData] = Field(
        description="List of checkpoints", default_factory=list
    )

    total_count: int = Field(
        description="Total number of available checkpoints", default=0
    )

    returned_count: int = Field(
        description="Number of checkpoints in this result", default=0
    )

    offset: int = Field(description="Offset used for this query", default=0)

    limit: int = Field(description="Limit used for this query", default=0)

    error_message: Optional[str] = Field(
        description="Error message if operation failed", default=None
    )

    execution_time_ms: int = Field(
        description="List operation execution time in milliseconds", default=0
    )

    timestamp: datetime = Field(
        description="When the list operation completed", default_factory=datetime.now
    )
