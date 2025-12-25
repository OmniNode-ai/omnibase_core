from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelBaseInputState(BaseModel):
    """Base model for all input states in ONEX"""

    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Metadata for the input state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the input was created",
    )
