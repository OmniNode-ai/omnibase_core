from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelBaseInputState(BaseModel):
    """Base model for all input states in ONEX.

    This is a base class for input state models that may be nested in other
    Pydantic models or used with pytest-xdist parallel test execution.
    The from_attributes=True setting ensures proper instance recognition
    across worker processes.
    """

    model_config = ConfigDict(from_attributes=True)

    metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Metadata for the input state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the input was created",
    )
