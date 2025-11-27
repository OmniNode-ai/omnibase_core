from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_message_type import EnumMessageType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelMessageContentBase(BaseModel):
    """Base message content with discriminator."""

    message_type: EnumMessageType = Field(
        default=...,
        description="Message type discriminator",
    )
    content: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Structured message content with proper typing",
    )
    priority: str = Field(default="normal", description="Message priority level")
    expiration_time: datetime | None = Field(
        default=None,
        description="Message expiration time",
    )
