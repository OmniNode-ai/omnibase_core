"""
LLM tool call model for structured tool usage.

Provides strongly-typed tool call model to replace Dict[str, Any] usage
in chat messages with proper ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLLMToolCallFunction(BaseModel):
    """Function details within a tool call."""

    name: str = Field(min_length=1, description="Name of the function to call")

    arguments: str = Field(description="JSON string of function arguments")

    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class ModelLLMToolCall(BaseModel):
    """
    Strongly-typed tool call model.

    Replaces Dict[str, Any] usage in tool call data
    with proper type safety and validation.
    """

    id: str = Field(min_length=1, description="Unique identifier for this tool call")

    type: str = Field(
        default="function",
        description="Type of tool call (typically 'function')",
    )

    function: ModelLLMToolCallFunction = Field(description="Function call details")

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
