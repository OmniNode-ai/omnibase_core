"""
Storage Result Base Model.

Strongly-typed model for storage backend operation results.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_checkpoint_data import ModelCheckpointData
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelStorageResult(BaseModel):
    """
    Model for storage backend operation results.

    Used by storage backends to return standardized operation
    results with success/failure information and data payloads.
    """

    success: bool = Field(description="Whether the operation succeeded")

    checkpoint_data: ModelCheckpointData | None = Field(
        description="Checkpoint data (for retrieval operations)", default=None
    )

    operation_type: str = Field(description="Type of storage operation")

    error_message: str | None = Field(
        description="Error message if operation failed", default=None
    )

    metadata: SerializedDict = Field(
        description="Operation metadata", default_factory=dict
    )

    execution_time_ms: int = Field(
        description="Operation execution time in milliseconds", default=0
    )

    affected_count: int = Field(
        description="Number of items affected by operation", default=0
    )

    timestamp: datetime = Field(
        description="When the operation completed", default_factory=datetime.now
    )
