from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_message_type import EnumMessageType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_message_content_base import (
    ModelMessageContentBase,
)


class ModelQueryMessageContent(ModelMessageContentBase):
    """Query message content for information requests."""

    message_type: Literal[EnumMessageType.QUERY] = Field(
        default=EnumMessageType.QUERY,
        description="Query message type",
    )
    query_type: str = Field(default=..., description="Type of query being performed")
    query_parameters: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Query parameters",
    )
    result_format: str = Field(default="json", description="Expected result format")
    max_results: int = Field(default=100, description="Maximum number of results")
    include_metadata: bool = Field(
        default=True,
        description="Whether to include result metadata",
    )
