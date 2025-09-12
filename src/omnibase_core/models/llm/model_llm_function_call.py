"""
LLM function call model for structured function calling.

Provides strongly-typed function call model to replace Dict[str, Any] usage
in chat messages with proper ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLLMFunctionCall(BaseModel):
    """
    Strongly-typed function call model.

    Replaces Dict[str, Any] usage in function call data
    with proper type safety and validation.
    """

    name: str = Field(min_length=1, description="Name of the function to call")

    arguments: str = Field(description="JSON string of function arguments")

    call_id: str | None = Field(
        default=None,
        description="Unique identifier for this function call",
    )

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
