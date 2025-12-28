from typing import Literal

from pydantic import Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.enums.enum_message_type import EnumMessageType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_message_content_base import (
    ModelMessageContentBase,
)


class ModelCommandMessageContent(ModelMessageContentBase):
    """Command message content for action requests."""

    message_type: Literal[EnumMessageType.COMMAND] = Field(
        default=EnumMessageType.COMMAND,
        description="Command message type",
    )
    command_name: str = Field(default=..., description="Name of the command to execute")
    command_parameters: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Command parameters",
    )
    execution_mode: str = Field(
        default="synchronous",
        description="Command execution mode",
    )
    timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Command timeout in milliseconds",
    )
    retry_policy: dict[str, int] = Field(
        default_factory=dict,
        description="Command retry policy configuration",
    )
