from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelBaseOutputState(BaseModel):
    """Base model for all output states in ONEX.

    This is a base class for output state models that may be nested in other
    Pydantic models or used with pytest-xdist parallel test execution.
    The from_attributes=True setting ensures proper instance recognition
    across worker processes.
    """

    model_config = ConfigDict(from_attributes=True)

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
