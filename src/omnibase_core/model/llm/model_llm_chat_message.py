"""
LLM chat message model for conversations.

Provides strongly-typed chat message model to replace dict usage in API requests
with proper ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_message_role import EnumMessageRole
from omnibase_core.model.llm.model_llm_function_call import ModelLLMFunctionCall
from omnibase_core.model.llm.model_llm_tool_call import ModelLLMToolCall


class ModelLLMChatMessage(BaseModel):
    """
    Strongly-typed LLM chat message model.

    Replaces dict usage in API request preparation
    with proper type safety and validation.
    """

    role: EnumMessageRole = Field(description="Role of the message sender")

    content: str = Field(min_length=1, description="Content of the message")

    name: str | None = Field(
        default=None,
        description="Name of the sender (for assistant messages)",
    )

    function_call: ModelLLMFunctionCall | None = Field(
        default=None,
        description="Function call data (for function calling)",
    )

    tool_calls: list[ModelLLMToolCall] | None = Field(
        default=None,
        description="Tool calls data (for tool usage)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
