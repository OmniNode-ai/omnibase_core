from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_message_type import EnumMessageType
from omnibase_core.models.operations.model_message_content_base import (
    ModelMessageContentBase,
)


class ModelDataMessageContent(ModelMessageContentBase):
    """Data message content for information transfer."""

    message_type: Literal[EnumMessageType.DATA] = Field(
        default=EnumMessageType.DATA,
        description="Data message type",
    )
    data_type: str = Field(default=..., description="Type of data being transferred")
    data_schema: str = Field(
        default=..., description="Schema identifier for data validation"
    )
    compression_used: bool = Field(
        default=False,
        description="Whether data is compressed",
    )
    checksum: str = Field(default="", description="Data integrity checksum")
    encoding: str = Field(default="utf-8", description="Data encoding format")
