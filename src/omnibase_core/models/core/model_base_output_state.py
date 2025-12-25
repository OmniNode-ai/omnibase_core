from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelBaseOutputState(BaseModel):
    """Base model for all output states in ONEX"""

    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Metadata for the output state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the output was created",
    )
    processing_time_ms: float | None = Field(
        default=None,
        description="Time taken to process in milliseconds",
    )
